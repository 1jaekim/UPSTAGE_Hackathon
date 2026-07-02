---
name: prescription-generator
description: Gate 1 승인 후, 안전 확인된 후보에서 정확히 5개를 골라 완전한 처방 항목으로 조립해야 할 때 이 Skill을 사용한다.
---

## 목적 및 범위
`safety_checked: true` 후보 중 우선순위 상위 5개를 처방 항목으로 조립한다. **용량·근거·출처는 라이브러리 값을 그대로 복사만 한다** — 생성·조정 금지가 [4-A]의 기계적 보장이자 dosage gap 봉합의 절반이다 (나머지 절반은 safety-judge completeness 재검증).
결과물: `work/40_prescription.json` 1개 — 정확히 5개, 전 항목 `safety_checked: true` + rationale 포함.
**실행 주체는 `scripts/generate_rx.py`(코드)다.**

## 작업 절차
1. spec.md에서 출력 형식(정확히 5개, 필수 필드)과 제약 [4-A]/[4-I]를 읽는다.
2. 실행: `python3 scripts/generate_rx.py` — 20_safety의 통과 목록 ∩ 10_candidates를 priority → name_en 순 정렬 후 상위 5개 선택, 라이브러리 값 verbatim 복사.
3. clamp된 후보는 intensity 서술에 제한 범위가 병기되는지 확인한다 (예: "(범위 제한: knee_flexion_max≤90)").
4. exit code를 해석한다: `0` 계속 / `14` 통과 후보 5개 미달(short) — 재검색 또는 에스컬레이션.
5. 성공 기준 대조: 정확히 5개 · 필수 필드(sets/reps/frequency/intensity/rationale/source) 전부 존재.

## 사용 규칙 및 제약 사항
- sets/reps/frequency/intensity/rationale/source는 exercise_library.json 값 그대로 — "조정"하는 순간 Gate 1 보장이 무효가 된다 (DECISIONS.md #5).
- 5개 미달 시 지어내지 않고 short:true로 종료한다 [4-A].
- 모든 운동에 rationale 포함 — 교육적 가치 [4-I].
- completeness 재검증에 필요한 속성(load_type, hamstring_load 등)을 항목에 동봉한다.

## 템플릿

```json
{
  "exercises": [
    { "name": { "ko": "대퇴사두근 등척성 수축", "en": "Quadriceps isometric set" },
      "sets": 3, "reps": 10,
      "frequency": { "ko": "1일 3회", "en": "3x daily" },
      "intensity": { "ko": "통증 없는 최대 수축 5초 유지", "en": "Pain-free maximal contraction, 5s hold" },
      "rationale": { "ko": "초기 대퇴사두근 활성화 및 근위축 방지, 이식건 부하 낮음",
                     "en": "Early quadriceps activation, prevents atrophy, minimal graft load" },
      "source": "SAMPLE_PROTOCOL.pdf#p3", "safety_checked": true,
      "load_type": "isometric", "hamstring_load": "none" }
  ],
  "short": false
}
```
