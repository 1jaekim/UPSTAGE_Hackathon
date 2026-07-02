---
name: corrector
description: safety-judge가 rejected_loop을 반환했을 때, 위반 룰의 correction_hint를 병합해 재검색 제약을 만들어야 할 때 이 Skill을 사용한다.
---

## 목적 및 범위
Gate 1 위반들의 correction_hint를 기계적으로 병합해 rag-recommender 재검색 조건을 생성한다. 교정은 판단이 아니라 규칙 병합이다.
결과물: `work/30_correction.json` 1개.
**실행 주체는 `scripts/correct.py`(코드)다. decision == rejected_loop일 때만 호출한다.**

## 작업 절차
1. spec.md에서 제약 [4-D]와 성공 기준(Gate 1의 bounded loop)을 읽는다.
2. 실행: `python3 scripts/correct.py` — `work/20_safety.json`의 violations[]를 읽어 병합한다:
   - `exclude` → 해당 운동 제외 + alternative_filter 병합 (동일 키는 룰 순서상 마지막 우선 — 룰 순서 고정이므로 결정론 유지)
   - `clamp` → 속성 상한/하한 항목 생성 (제외 대신 수정으로 후보를 살림)
   - `force_isometric` (REDFLAG-01) → 모든 동적 운동 등척성 강제 치환 [4-D]
3. `iteration += 1` 확인 — max 5 초과 판정은 safety-judge 몫.
4. 이후 rag-recommender 재검색 → safety-judge 재판정 (run_pipeline.py가 자동 루프).

## 사용 규칙 및 제약 사항
- approved/failed 상태에서 호출 금지 — 스크립트가 거부(die)한다.
- LLM이 "더 나은 대체 운동"을 창작하는 것 금지 — 재검색은 항상 rag-recommender(데이터 바운드) 경유 [4-A].
- 30_correction.json을 수작업 편집하지 않는다.

## 템플릿

```json
{
  "iteration": 2,
  "exclude": ["Heel slide (0–90°)"],
  "add_filters": { "load_type_in": ["isometric"] },
  "clamps": [ { "name_en": "Heel slide (0–90°)", "field": "knee_flexion_max", "op": "max", "value": 90 } ],
  "force_isometric": true,
  "reason": "REDFLAG-01(Ankle pumps); REDFLAG-01(Straight leg raise (SLR))"
}
```
