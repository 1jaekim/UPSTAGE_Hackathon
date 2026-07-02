 # SafeRx v2 — 코드 우선 재구성

> 원칙: **LLM은 언어가 필요한 곳에만.** 코드로 판정 가능한 모든 것은 코드로.
> spec.md(원본 유지)가 최상위 규범. 미결/모호 사항의 구현 결정은 DECISIONS.md 참고.

## 구조

```
saferx-v2/
├── spec.md                  # 원본 그대로 (최상위 규범)
├── DECISIONS.md             # spec 미결 사항의 구현 결정 8건
├── data/
│   ├── rule_table.json      # 22개 룰 (ACL-HS-BWH-v1) ⚠️SAMPLE
│   ├── exercise_library.json# 팀 제작 30개 (v2-team) ⚠️dosage placeholder
│   ├── exercise_movement_map.csv / sources.csv  # 팀 원본 (빌더: scripts/build_library.py)
│   └── week_phase_map.json  # §4-G 잠정 매핑 (팀 결정 대기)
├── scripts/                 # 전부 결정론적 코드 (stdlib only, LLM 아님)
│   ├── lib.py               # 조건 매처, phase 로직, IO
│   ├── extract_redact.py    # 1. pass-through + 정규식 redaction + scope gate
│   ├── retrieve.py          # 2. 데이터 바운드 후보 검색 (ChromaDB 훅 자리 표시)
│   ├── safety_judge.py      # 3. Gate 1 안전 판정 + completeness 재검증 ⭐핵심
│   ├── correct.py           # 4. 교정 계획 (correction_hint 병합)
│   ├── generate_rx.py       # 5. 처방 5개 조립 (라이브러리 값 복사만)
│   ├── fetch_protocol.py    # 1.5 ChromaDB 프로토콜 근거 컨텍스트 (non-fatal)
│   ├── report_validate.py   # 7. Gate 3 + 기계적 J2/J3/J5/J6
│   └── run_pipeline.py      # 코드 구간 일괄 러너 (교정 루프 포함)
├── skills/                  # 재사용 절차 6개 (5개는 스크립트 실행 절차, report-writer만 LLM 수행)
│   ├── info-extractor/      #  → scripts/extract_redact.py
│   ├── rag-recommender/     #  → scripts/retrieve.py
│   ├── safety-judge/        #  → scripts/safety_judge.py ⭐권위 판정
│   ├── corrector/           #  → scripts/correct.py
│   ├── prescription-generator/ # → scripts/generate_rx.py
│   └── report-writer/       #  🟢 유일한 LLM 수행 스킬 (reporter-subagent가 실행)
├── agents/
│   ├── acl-safety-orchestrator/     # 메인 (solar) — 흐름 제어
│   │   ├── AGENT.md                 #  역할표·실행 흐름·체크리스트
│   │   └── subagents/               #  소유: thin executor 5개 (solar, 판단 없음)
│   │       ├── info-extractor-subagent/   → scripts/extract_redact.py
│   │       ├── rag-recommender-subagent/  → scripts/retrieve.py
│   │       ├── safety-judge-subagent/     → scripts/safety_judge.py
│   │       ├── corrector-subagent/        → scripts/correct.py
│   │       └── generator-subagent/        → scripts/generate_rx.py
│   ├── reporter-subagent/           # 독립 (solar-pro) — 생성: SOAP 서술
│   └── report-judge-subagent/       # 독립 (solar-pro) — 판단: Gate 2 (J1·J4)
├── samples/personas/        # 환자 페르소나 30명 (트리거 입력 JSON + _index)
└── data/patients_soap_30.csv# 페르소나 원본 (변환: scripts/convert_personas.py)
```

## 실행

```bash
python3 scripts/run_pipeline.py samples/case_normal.json
cat work/99_status.json     # ready_for_reporter → 이후 LLM 단계
```

상태 코드: `ready_for_reporter` / `unsupported_surgery` / `manual_review_required`
/ `insufficient_evidence` / `failed`

## 검증 결과 — 페르소나 배치 30/30 통과

`CHROMA_API_KEY="" python3 scripts/run_batch.py samples/personas`

| 그룹 | 인원 | 기대 → 실제 |
|---|---|---|
| ACL_HS 정상 경로 | 6 | ready_for_reporter ✅ (phase 적합 처방 5개) |
| ACL_HS red flag (P001·P003) | 2 | ⚠️ insufficient_evidence — PHASE_I 등척성 1개뿐 (데이터 공백, DECISIONS #12) |
| ACL_HS + 동반시술 (P009) | 1 | manual_review_required ✅ |
| 스코프 밖 수술 (THA/RCR/아킬레스) | 21 | unsupported_surgery ✅ |

- Red flag 2건(P001 부종 중등도, P003 부종+NRS5): 교정 루프 → 전량 등척성 ✅
- 주차↔단계 불일치(P003~P007 등): 낮은 phase 보수 채택 + 플래그 ✅
- 트랩(P005 11주차 러닝 요구): PHASE_II 처방에 러닝·충격 운동 미포함 ✅

## 단위 검증 (개발 중 확인)

| 케이스 | 기대 동작 | 결과 |
|---|---|---|
| 정상 (PHASE_I, NRS3) | 승인 → 처방 5개 | ✅ (1회 판정) |
| Red flag (NRS8+부종) | §4-D 루프 → 전량 등척성 치환 | ✅ (iter2에서 승인) |
| TKA | unsupported_surgery 즉시 종료 | ✅ |
| 동반 시술 | manual_review 에스컬레이션 | ✅ |
| week2↔PHASE_IV 충돌 | PHASE_I 보수 채택 + 플래그 | ✅ |
| 재현성 | 동일 입력 2회 → 판정·처방 바이트 동일 | ✅ |
| DOS-02 | 용량 변조(sets 3→10) 탐지 | ✅ fail 검출 |
| Gate 3 | 운동 4개 변조 리포트 검출 | ✅ V-J2 fail |
| Redaction | 이름/전화/기관/주민번호 마스킹, age→밴드 | ✅ |

## 프로덕션 전 필수 작업
1. ~~운동 데이터 교체~~ → 완료 (팀 movement map). 남은 것: dosage 확정 + PHASE_I 등척성 보강 + rule_table 잔여 수치 검증
2. `week_phase_map.json` 팀 확정 (§4-G)
3. ~~ChromaDB 연동~~ → 완료 (`rag/` + `scripts/fetch_protocol.py`, 근거 컨텍스트 방식 — DECISIONS #10). 사용자 환경에서 Cloud 실연동 1회 확인 필요
4. 이름 redaction NER 보강 (현재는 보수적 정규식)
5. 제3자 LLM 사용 시 §4-F 법무/DPO 검토
