# Timely에 Judge/Corrector 스킬(결정론 엔진) 붙이기

Timely AI 답변으로 파일 번들링 + `python3` 실행 + `shared_workspace`가 다 된다는 게
확인됨 → **외부 HTTP 서버 배포 없이** `saferx-harness/engine/`을 그대로 Timely 안에서
실행하는 방식으로 간다. `tests/run_tests.py` 7/7 통과 확인된 코드라 그대로 가져다 쓰면 됨.

## 1. 번들할 파일 (Timely `skill.create`의 `files`에 첨부)

| 로컬 경로 | 스킬 안에서의 경로 |
|---|---|
| `saferx-harness/engine/rules_engine.py` | `engine/rules_engine.py` |
| `saferx-harness/engine/correction_planner.py` | `engine/correction_planner.py` |
| `saferx-harness/data/rule_table.json` | `data/rule_table.json` |
| `saferx-harness/data/exercise_db.json` | `data/exercise_db.json` |

경로 구조를 그대로 유지해야 한다 — 두 스크립트 모두 `os.path.join(HERE, "..", "data", ...)`로
상대경로 참조를 하드코딩하고 있음(`engine/` 옆에 `data/`가 있어야 함).

`shared_workspace: true`로 설정 — Judge가 candidate 단계에서 한 번, Corrector 이후
재검증(prescription 단계)에서 또 한 번 같은 파일을 읽으므로, 매 스텝마다 파일이 새로
복사되는 것보다 세션 내내 유지되는 게 안전하고 빠름.

## 2. Judge 스텝 (safety-validator 서브에이전트)

**실행할 bash 명령:**
```bash
python3 engine/rules_engine.py \
  --ctx '{"week": 2, "graft_type": "hamstring_autograft", "pain_nrs": null, "swelling": false}' \
  --exercises heel_slide_110 quad_set \
  --stage candidate
```
- `--ctx`는 그 시점까지 파이프라인에 쌓인 환자 상태(JSON)를 그대로 문자열로 넣는다.
- `--exercises`는 RAG가 반환한 운동 ID 목록.
- `--stage`는 candidate(운동별 임상 규칙) 또는 prescription(Generator 이후 완전성 검증) 중 하나.

**출력** (stdout, 그대로 파싱해서 다음 노드로 전달):
```json
{
  "passed": false,
  "violations": [
    {"exercise_id": "heel_slide_110", "rule_id": "ROM-01", "category": "range_of_motion",
     "priority": 90, "reason": "...", "message": "...", "source": "Brigham ACL Protocol"}
  ],
  "manual_review_items": [...]
}
```

**⚠️ 중요 — 서브에이전트의 마지막 응답 형식**: 로깅 훅(`hooks_server.py`)이 `SubagentStop`의
`last_assistant_message`를 파싱해서 로그를 남기므로, Judge 서브에이전트는 bash 실행 후
**최종 응답을 반드시 아래 봉투 형태 JSON 하나로만** 끝내야 한다 (2000자 제한 있음 —
violations가 많으면 rule_id/exercise_id만 남기고 reason/message는 생략 고려):
```json
{"agent": "safety-validator", "attempt": 1, "event": "judge_result",
 "payload": {"passed": false, "violations": [...]}}
```

## 3. Corrector 스텝 (correction-planner 서브에이전트, 위반 있을 때만, 1회)

**실행할 bash 명령:**
```bash
python3 engine/correction_planner.py \
  --ctx '{"week": 2, "graft_type": "hamstring_autograft"}' \
  --violations '[{"exercise_id": "heel_slide_110", "rule_id": "ROM-01", "category": "range_of_motion", "priority": 90}]'
```
- `--violations`는 Judge가 방금 낸 `violations` 배열을 그대로 문자열로 전달.

**출력:**
```json
{
  "exclude_exercises": ["heel_slide_110"],
  "add_filters": {"rom_max": 90},
  "substitutions": [],
  "manual_review_required": false,
  "manual_review_reasons": [],
  "changelog": [{"violation": "ROM-01", "action": "add_rom_filter", "rom_max": 90, "excluded": "heel_slide_110"}]
}
```
이 출력은 **새 처방이 아니라 RAG 재검색 조건** — `exclude_exercises`/`add_filters`를
RAG(exercise-retriever) 스텝에 다시 넘겨서 재검색시킨 뒤, Judge를 다시 호출(재검증)한다.

**Judge와 동일하게, 마지막 응답은 훅 로깅용 봉투로 감싸서 끝내야 함:**
```json
{"agent": "correction-planner", "attempt": 1, "event": "corrector_changelog",
 "payload": {"exclude_exercises": [...], "changelog": [...]}}
```

## 4. 흐름 요약 (Plan B, workflow.md 그대로)

```
RAG(candidate_ids)
  → Judge(--stage candidate) → passed? ─Yes→ Generator
                              └─No──→ Corrector(1회) → RAG(재검색) → Judge(재검증)
                                                                      → passed? ─Yes→ Generator
                                                                      └─No──→ manual_review_required 승계 → Generator
  → Generator(처방) → Judge(--stage prescription, 완전성) → Reporter
```

## 5. 확인 완료 사항

- `python3 tests/run_tests.py` 로컬 실행 결과: **7/7 통과** (TC-2 재현성 3회 동일 포함)
- 두 스크립트 모두 표준 라이브러리만 사용 (`json`, `os`, `sys`, `argparse`) — pip install 불필요
- Timely 쪽 확인된 사항: Python 3.12 기본 설치, `bash`/`command` 툴로 실행 가능, `files` 파라미터로 파일 번들링 가능, `shared_workspace: true`로 세션 내 파일 유지 가능
