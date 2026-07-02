---
name: safety-judge
description: 후보 운동의 안전성(Gate 1) 또는 최종 처방 5개의 완결성을 22개 룰 테이블 대조로 판정해야 할 때 이 Skill을 사용한다.
---

## 목적 및 범위
`data/rule_table.json`(ACL-HS-BWH-v1, 22개 룰) 대조로 시스템의 권위 안전 판정을 내린다. 재현성이 존재 이유이므로 **판정은 코드(`scripts/safety_judge.py`)가 수행하며, LLM 판단을 넣는 것은 spec 위반이다.**
결과물: safety 모드 → `work/20_safety.json` / completeness 모드 → `work/45_completeness.json`

## 작업 절차
1. spec.md에서 성공 기준(Gate 1)과 제약 [4-D]를 읽는다.
2. Gate 1: `python3 scripts/safety_judge.py --mode safety` — 각 후보 × safety 룰(FIRE = patient_if AND exercise_if 매치) 평가.
3. 집계 판정을 확인한다: hard 위반(운동×룰 쌍) `0 → approved` / `1–10 → rejected_loop` / `≥11 → failed`, `iteration > 5 → failed` 강등. soft(REDFLAG-02/WB-02/RTS-01)는 카운트 제외, manual_review로만 수집.
4. 완결성 체크(처방 조립 후): `python3 scripts/safety_judge.py --mode completeness` — 최종 5개에 안전 룰 **재평가**(clamp·용량 반영 상태 기준) + COMP-01/02(필드 누락) + DOS-02(용량이 라이브러리 초과 시 fail).
5. exit code를 해석한다: safety `0/20/21/13(input gate)` · completeness `0/22`.

## 사용 규칙 및 제약 사항
- LLM이 판정을 대신·보정·재해석하거나 결과 JSON을 수정하는 것 금지 (spec Gate 1 — 결정론적, 권위 판정).
- Gate 1이 approved가 아니면 Gate 2(report-judge)를 절대 진행하지 않는다.
- input gate(GATE-01/02/03) FIRE 시 즉시 short-circuit — 위반 카운트에 넣지 않는다.
- 판정 단위·임계값 정의는 DECISIONS.md #1을 따른다.

## 템플릿

```json
{
  "mode": "safety", "decision": "rejected_loop", "hard_violations": 5,
  "violations": [
    { "rule_id": "REDFLAG-01", "title": "Red flag 시 동적 운동 금지",
      "exercise": "Ankle pumps", "quote_ref": "spec [4-D]",
      "correction_hint": { "action": "force_isometric",
                           "alternative_filter": { "load_type_in": ["isometric"] } } }
  ],
  "manual_review": [], "iteration": 1,
  "exercises_checked": [ { "name_en": "Quadriceps isometric set", "safety_checked": true } ]
}
```
