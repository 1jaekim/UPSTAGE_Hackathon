---
name: report-writer
description: 완결성 체크까지 통과한 처방 5개와 관찰치를 이중언어 SOAP JSON 리포트로 서술해야 할 때 이 Skill을 사용한다. 파이프라인 유일의 LLM 수행(생성) 스킬이다.
---

## 목적 및 범위
처방 5개 + 환자 컨텍스트를 SOAP 4섹션의 이중언어(ko+en) 서술로 렌더링한다. **임상적 실질은 이미 코드가 결정한 상태** — 이 스킬의 역할은 결정된 사실의 서술화뿐이다.
결과물: `work/50_report.json` 1개 — spec 출력 형식 스키마, A4 1장(서술 ≤3,500자), Plan에 정확히 5개.
수행 주체: reporter-subagent (LLM, solar-pro).

## 작업 절차
1. spec.md에서 출력 형식(섹션 순서·분량)과 제약 [4-H]/[4-I]를 읽는다.
2. 입력 읽기: `work/00_context.json` + `work/40_prescription.json` (+ `work/45_completeness.json`의 manual_review 항목).
3. SOAP 4섹션을 작성한다 (모두 ko+en):
   - Subjective: age_band + 주호소 (`notes_redacted`만 근거로; age_band는 이 섹션에만 등장)
   - Objective: 주차·유효 phase·부종·NRS·이식건 (phase_week_mismatch 시 "낮은 단계 보수 채택" 명시)
   - Assessment: 단계 판단·주의·red flag 상태 — 제안 화법만
   - Plan: 2–3문장 요약 + exercises 5개 **verbatim 복사**
4. report_meta(record_id는 오케스트레이터 부여) · manual_review[] · safety를 채운다.
5. 성공 기준 대조: report_validate.py의 기계 체크 항목(5개·필드·이중언어·길이)을 스스로 점검 후 저장.

## 사용 규칙 및 제약 사항
- 5개 운동의 name/sets/reps/frequency/intensity/rationale/source/safety_checked는 40_prescription.json에서 한 글자도 바꾸지 않는다 — 추가·삭제·순서 변경·용량 재서술("1일 3회"→"하루 두세 번") 전부 금지. 위반은 Gate 2 J4와 DOS-02가 이중으로 잡는다.
- 마스킹된 내용([이름], [기관명])의 추측 복원 금지 [4-F].
- 진단 언어·확정 지시 금지, 제안+근거만 [4-I]. 데이터 밖 서술·무출처 항목·게이트 탈락 운동 포함 금지 [4-A].
- 재생성 모드: `work/55_validation.json`의 실패 목록이 주어지면 **지적된 문제만** 수정 (전면 재작성 금지 — 통과 부분 재파손 방지).

## 템플릿

```json
{
  "report_meta": { "record_id": "rec_0007", "surgery": "ACL_RECON", "week_post_op": 2,
    "phase": "PHASE_I", "graft_type": "hamstring_autograft", "format": "SOAP",
    "language": "ko-en", "protocol_source": { "name": "...", "url": "..." },
    "generated_at": "2026-07-02T00:00:00Z" },
  "soap": {
    "subjective": { "ko": "30대 환자. 계단 하강 시 불안감 호소.", "en": "Patient in their 30s. ..." },
    "objective":  { "ko": "수술 후 2주차, PHASE_I. 부종 없음, NRS 3.", "en": "Post-op week 2, ..." },
    "assessment": { "ko": "초기 보호기로 판단됨. Red flag 없음. ... 제안됨.", "en": "..." },
    "plan": { "ko": "PHASE_I 목표는 ...", "en": "...",
      "exercises": [ { "name": { "ko": "...", "en": "..." }, "sets": 3, "reps": 10,
        "frequency": { "ko": "...", "en": "..." }, "intensity": { "ko": "...", "en": "..." },
        "rationale": { "ko": "...", "en": "..." }, "source": "...", "safety_checked": true } ] }
  },
  "manual_review": [ { "item": "quadriceps_strength_criterion",
    "note": { "ko": "PT 수동 확인 필요", "en": "PT manual review required" } } ],
  "safety": { "final_gate_passed": true, "violations": [] }
}
```
