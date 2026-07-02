---
name: info-extractor
description: ACL SafeRx 파이프라인의 최초 단계로, 트리거 입력을 정규화·마스킹하고 scope gate를 판정해야 할 때 이 Skill을 사용한다.
---

## 목적 및 범위
트리거 입력(JSON)을 정규화하고, notes를 코드로 마스킹하며, 지원 범위 밖 케이스를 조기 종료시킨다.
결과물: `work/00_context.json` 1개 — pass-through 필드 + `notes_redacted` + `age_band` + `flags` 포함.
**실행 주체는 `scripts/extract_redact.py`(코드)다. LLM은 실행·해석만 하고 어떤 단계도 직접 수행하지 않는다.**

## 작업 절차
1. spec.md에서 범위(포함/제외)와 제약 [4-B]/[4-C]/[4-E]/[4-F]/[4-G]를 읽는다.
2. 실행: `python3 scripts/extract_redact.py <trigger_input.json>`
3. exit code를 해석한다: `0` 계속 / `10` unsupported_surgery 즉시 종료 / `11` manual_review_required 에스컬레이션 종료.
4. `work/00_context.json`의 flags가 입력과 일치하는지 대조한다 (phase_week_mismatch, red_flag 포함).

## 사용 규칙 및 제약 사항
- 구조화 필드(surgery, week_post_op, pain_nrs, swelling, phase, graft_type)는 재파싱하지 않고 그대로 전달한다 [4-B].
- notes에서 판단 필드를 새로 만들지 않는다 — `notes_redacted`는 리포트 Subjective 참고 전용 [4-C].
- 마스킹(주민번호·전화·기관명·성+이름+호칭)과 age 밴드화는 **LLM에 원문이 닿기 전** 정규식 코드로 수행된다 [4-F]. LLM이 redaction을 대신하는 것 금지.
- week↔phase 충돌 시 낮은 단계 보수 채택 + `phase_week_mismatch` 플래그 [4-G].
- 스크립트 출력(00_context.json)을 사후 수정하지 않는다.

## 템플릿

```json
{
  "surgery": "ACL_RECON", "week_post_op": 2,
  "phase": "PHASE_I", "phase_declared": "PHASE_I", "phase_derived_from_week": "PHASE_I",
  "graft_type": "hamstring_autograft", "pain_nrs": 3, "swelling": false,
  "age_band": "30s", "notes_redacted": "[이름], [전화번호], [기관명]에서 수술. ...",
  "flags": { "unsupported_surgery": false, "manual_review_required": false,
             "manual_review_reason": null, "phase_week_mismatch": false, "red_flag": false }
}
```
