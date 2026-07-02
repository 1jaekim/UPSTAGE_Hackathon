# Timely 에이전트 설계용 입력 스키마

프론트엔드(`src/api/harness.ts`)가 Timely 트리거로 보내는 요청의 계약. 각 에이전트/스킬을
설계할 때 "내가 어떤 필드를 받는지, 그 필드가 이미 구조화되어 있는지"를 확인하는 용도.

## ⚠️ 먼저 확인할 것 — input-parser 역할이 원래 spec보다 가볍다

`saferx-harness/spec.md` §3은 `surgery_name`을 **자유텍스트**로 받아서 `input-parser`가
`concomitant_procedure`/`pain_nrs`/`swelling`/`graft_type`을 파싱해내는 걸 전제로 한다.

하지만 **실제 프론트엔드는 이미 이 필드들을 구조화해서 보낸다** (드롭다운/체크박스/숫자
입력으로 받으므로): `surgery`, `pain_nrs`, `swelling`, `phase`, `graft_type` 전부 파싱이
필요 없는 상태로 도착한다. `input-parser`가 실제로 자연어 처리를 해야 하는 대상은
**`notes` 필드(자유 텍스트) 하나뿐**이고, 그마저도 위 구조화 필드에서 이미 잡힌 내용을
재추출하는 게 아니라 "구조화 필드가 못 담은 나머지 특이사항"을 위한 보조 채널이다.

`input-parser`를 설계할 때 이미 도착한 구조화 필드를 다시 텍스트로 되돌려 파싱하는
로직을 만들 필요는 없다 — 그대로 통과시키면 된다.

## 트리거 입력 JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SafeRxHarnessTriggerInput",
  "type": "object",
  "required": ["surgery", "week_post_op", "age", "swelling", "notes", "surgery_details"],
  "properties": {
    "surgery": { "type": "string", "enum": ["ACL_RECON"] },
    "week_post_op": { "type": "integer", "minimum": 0 },
    "age": { "type": "integer", "minimum": 1 },
    "concomitant_procedure": { "type": ["string", "null"] },
    "pain_nrs": { "type": ["integer", "null"], "minimum": 0, "maximum": 10 },
    "swelling": { "type": "boolean" },
    "notes": { "type": "string" },
    "surgery_details": {
      "type": "object",
      "description": "surgery 값에 따라 모양이 달라짐. ACL_RECON일 때는 아래 예시 참고.",
      "required": ["phase", "graft_type"],
      "properties": {
        "phase": { "type": "string", "enum": ["PHASE_I", "PHASE_II", "PHASE_III", "PHASE_IV", "PHASE_V"] },
        "graft_type": { "type": "string", "enum": ["hamstring_autograft"] }
      }
    }
  },
  "additionalProperties": false
}
```

## 예시 페이로드

```json
{
  "surgery": "ACL_RECON",
  "week_post_op": 2,
  "age": 45,
  "concomitant_procedure": null,
  "pain_nrs": null,
  "swelling": false,
  "notes": "",
  "surgery_details": {
    "phase": "PHASE_I",
    "graft_type": "hamstring_autograft"
  }
}
```

동반 술식·통증이 있는 케이스:

```json
{
  "surgery": "ACL_RECON",
  "week_post_op": 3,
  "age": 52,
  "concomitant_procedure": "반월판 봉합",
  "pain_nrs": 6,
  "swelling": true,
  "notes": "환자가 계단 오르내리기 시 불안정감 호소",
  "surgery_details": {
    "phase": "PHASE_II",
    "graft_type": "hamstring_autograft"
  }
}
```

## 필드별 설명 + 어느 스킬이 쓰는지

| 필드 | 타입 | 이미 구조화됨? | 설명 | 주로 쓰는 스킬 |
|---|---|---|---|---|
| `surgery` | enum | ✅ | 수술 코드. 지금은 `"ACL_RECON"` 하나뿐 | `scope-gate` (지원 여부 즉시 판정 → 아니면 `unsupported_surgery` 종료), 이후 전 스킬이 분기 기준으로 참조 |
| `week_post_op` | int | ✅ | 수술 후 회복 주차 | `exercise-retriever`(ChromaDB 검색 필터), `safety-validator`(`rule_table.json`에서 단계 조회 키) |
| `age` | int | ✅ | 환자 나이 | 현재 규칙 판정에는 안 쓰임. `report-writer`가 SOAP Subjective에 기재 |
| `concomitant_procedure` | string\|null | ✅ | 동반 술식 (반월판 봉합 등) | `scope-gate` — 값이 있으면 규칙셋이 통째로 달라지므로 `manual_review_required: true, reason: "concomitant_procedure"`로 즉시 승계하고 `safety-validator`는 이 케이스를 평가하지 않음 (spec §6-E) |
| `pain_nrs` | int(0-10)\|null | ✅ | 통증 수준(NRS) | `safety-validator`의 red flag 판정 (spec §6-D) — 임계값 넘으면 동적 운동 자동 실패 |
| `swelling` | bool | ✅ | 부종 여부 | `safety-validator`의 red flag 판정. red flag 성립 시 `correction-planner`가 전부 등척성(isometric) 운동으로 강제 치환 |
| `notes` | string | ❌ (자유 텍스트) | 구조화 필드가 못 담은 나머지 특이사항 | `input-parser`가 참고용으로만 훑음. 여기서 새로 뭔가를 구조화해서 뒷단 판정에 쓰지 않음(비결정성 유입 방지, spec §6-B/C) |
| `surgery_details.phase` | enum | ✅ | 재활 단계 (Phase I~V, knee ACL 프로토콜 문서 구조와 일치) | `exercise-retriever`(ChromaDB 검색 필터), `safety-validator`(단계별 규칙 조회 키) |
| `surgery_details.graft_type` | enum | ✅ | 이식건 종류. 지금은 `"hamstring_autograft"` 하나뿐 | `exercise-retriever`/`safety-validator` — 이식건별 특이 규칙이 생기면 분기 기준 |

## 스킬 파이프라인 순서 (참고)

`workflow.md`(Plan B, 정본) 기준:

```
입력 → input-parser → scope-gate → exercise-retriever → safety-validator
  → (fail) correction-planner → exercise-retriever(재검색) → safety-validator(재검증)
  → prescription-writer → safety-validator(완전성 검증) → report-writer → 웹 출력
```

## 확장 시 체크리스트 (다른 수술 추가할 때)

1. ChromaDB에 해당 수술 프로토콜 문서 적재 (근거 없이 값만 추가 금지 — spec §6 "insufficient_evidence")
2. `surgery` enum에 값 추가
3. `surgery_details`에 그 수술 전용 필드 정의 (예: 회전근개면 `repair_size`, `passive_only_until_week` 등 — ACL의 `phase`/`graft_type`과 동일한 위치, 다른 내용물)
4. `data/rule_table.json`에 해당 수술 조건의 Judge 규칙 추가
5. 프론트 `src/types.ts`에 `XxxSurgeryDetails` 인터페이스 추가 + `SurgeryDetails` 유니온 확장, `src/api/harness.ts`의 `toWireSurgeryDetails()`에 분기 추가
