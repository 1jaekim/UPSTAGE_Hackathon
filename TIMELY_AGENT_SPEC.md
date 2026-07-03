# SafeRx Harness — Timely 에이전트 이식 스펙

이 문서는 현재 `rag/harness/` 아래 구현되어 있는 **결정론적 안전성 검증 하네스**를,
Timely(자연어 기반 노코드 에이전트 플랫폼)의 에이전트/스킬 구조로 그대로 옮기기 위한
전체 명세다. 현재 프론트엔드(React 체크박스 폼)는 구조화 입력을 만들기 위한 **하나의
인터페이스일 뿐**이고, 하네스의 본체(안전 판정 로직·규칙표·SOAP 리포트 생성)는 입력
방식과 무관하게 동일해야 한다. 즉 Timely에서는 "자연어 입력 → 동일한 구조화 필드
추출"이라는 새 앞단 하나만 추가되고, 그 뒤 파이프라인은 1:1로 그대로 이식하면 된다.

---

## 0-a. 데이터 출처 — ChromaDB/프로토콜 PDF는 런타임에 안 쓴다 (중요)

`rag/protocols/`에 실제 프로토콜 PDF(`knee.pdf`, `shoulder.pdf`, `achilles.pdf`,
`hip.pdf`)와, 이를 파싱해 ChromaDB(`rehab_protocols` 컬렉션)에 적재하는
`ingest_protocols.py`/`query_protocols.py`가 존재한다. 이건 프로젝트 초기 RAG
프로토타입 단계의 산물이고, **현재 하네스 파이프라인(4단계 Retrieve, 5단계 Safety
Judge)은 이걸 전혀 호출하지 않는다** — `retrieve.py`는 오직 정적 파일
`exercise_library.json`/`rule_table.json`만 읽는다.

역할을 명확히 구분해야 한다:

| | 원본 프로토콜 PDF | ChromaDB 실시간 검색 | 정적 JSON (`rule_table.json`, `exercise_library.json`) |
|---|---|---|---|
| 용도 | 규칙표·운동 라이브러리를 **작성·검증**하는 원자료(출처 문헌) | 초기 프로토타입의 RAG 검색 UI (현재 미사용) | 런타임에 실제로 대조되는 결정론적 데이터 |
| 언제 쓰이나 | 사람(+LLM 보조)이 규칙표를 큐레이션/검수할 때, **오프라인·일회성** | 안 씀 | 매 요청마다 코드가 읽음 |
| 재현성에 영향? | 없음 (런타임 미개입) | **있음** — 임베딩 유사도 top-k는 흔들릴 수 있어 안전 판정에 쓰면 재현성 원칙 위반 | 없음 (파일 내용이 고정이면 결과도 고정) |

**결론**: Timely에 이식할 때 "PDF를 실시간으로 검색해서 안전 판정에 쓰는" RAG 스텝을
새로 만들 필요는 없고, 만들어서도 안 된다(§0의 재현성 원칙 위반). 대신:

1. **PDF 원본은 그대로 팀에 인계**해서, `rule_table.json`/`exercise_library.json`의
   "SAMPLE — 원문 대조 필요" 표시를 실제 프로토콜 문구와 대조·확정하는 데 쓴다. 이
   대조 작업은 사람이 검수하는 **오프라인 저작(authoring) 과정**이지, 파이프라인의
   런타임 단계가 아니다. (LLM으로 초안을 뽑더라도 최종본은 사람이 승인한 정적 파일로
   고정해야 한다.)
2. **완성된 정적 데이터(규칙표·운동 라이브러리)만 Timely 쪽 코드/함수 노드에 그대로
   업로드**한다 — 이게 4~7단계, 특히 5단계(Safety Judge)가 참조하는 유일한 지식
   소스가 되어야 한다.
3. `report_meta.protocol_source`(리포트에 인용되는 출처 표기, 예: "Brigham and
   Women's Hospital, Department of Rehabilitation Services")는 이 원본 문헌들을
   가리키는 값이므로, 실제 서비스 전 저작권/인용 표기 요건도 함께 확인해야 한다.
4. Chroma Cloud 자체는 하네스와 별개로 `hooks_server.py`의 `execution_logs`
   컬렉션(요청 로깅용)에서만 쓰인다 — 이건 안전 판정과 무관한 감사(audit) 목적이므로
   이식 여부는 선택 사항이다.

---

## 0. 하네스 엔지니어링 핵심 원칙 (모든 에이전트/스킬이 지켜야 할 제약)

이 원칙들은 개별 스킬 구현보다 우선한다. Timely에서 어떤 노드를 쓰든 아래를 위반하면
안 된다.

1. **안전 판정은 절대 LLM이 하지 않는다.** 운동이 안전한지/위험한지 판단하는 것은
   100% 규칙표(rule table) 대조 코드다. LLM은 (a) 자연어 파싱, (b) 이진 스크리닝
   신호, (c) 서술문 생성, (d) 서술 품질 검수 4곳에만 관여하고, 이 4곳 모두 "그 자체로
   안전 여부를 판단"하지 않는다.
2. **재현성 (Reproducibility)**: 같은 입력 → 항상 같은 출력. 검증 방법은 동일 입력을
   3회 실행해 결정론적 산출물(SHA256)이 완전히 같은지 비교하는 것. LLM 호출이 들어가는
   지점(자연어 파싱, 서술 생성, 서술 검수)은 "표현은 달라도 결과 상태(state)는 항상
   같아야" 이 기준을 만족한다 — 아래 "이진 스크리닝 패턴" 참고.
3. **이진 스크리닝 패턴**: LLM에게 뉘앙스 있는 판단을 맡기지 않는다. LLM 호출의 산출은
   반드시 `true/false` 같은 이진값이고, `true`가 나왔을 때 뒤따르는 동작은 **항상
   고정된 하나의 동작**이다 (예: "특이사항에 우려되는 내용 있음=true → 무조건 PT에게
   위임"). 이러면 LLM 표현이 매번 달라져도 파이프라인 상태 전이는 재현 가능하다.
4. **Fail-closed / PT 위임**: 자동 판정이 확신할 수 없으면 운동을 지어내지 않고
   사람(담당 물리치료사)에게 넘긴다. 절대로 "그럴듯한" 운동을 추측해서 만들어내지 않는다.
5. **데이터 바운드 (§4-A)**: 최종 처방에 들어가는 운동의 이름/근거(rationale)/출처
   (source)는 라이브러리에 있는 값을 **토씨 하나 안 틀리고 그대로 복사**한다. LLM이
   운동 이름이나 근거를 새로 만들거나 바꾸는 것은 금지.
6. **PII 최소화**: 나이는 연령대(decade band)로, 자유 텍스트는 정규식 기반 마스킹
   후에만 LLM에 전달한다. 원본 PII가 LLM 프롬프트에 들어가는 경로는 없어야 한다.
7. **세트/반복/빈도(dosage)는 시스템이 정하지 않는다.** 이건 담당 물리치료사의 재량
   영역이라 처방 항목에 아예 포함하지 않는다 (팀 결정, 과거엔 포함했다가 제거함).
8. **다양성도 결정론적으로**: 후보 풀에서 최종 처방 N개를 뽑을 때 "진짜 무작위"나
   "LLM이 골라주는" 방식을 쓰지 않는다. 환자의 **구조화 필드**(자유 텍스트 제외)를
   해시한 값을 시드로 쓰는 의사난수 조합 선택을 쓴다 — 같은 환자는 항상 같은 조합,
   다른 환자는 다른 조합이 나오되 재현성은 깨지지 않는다.

---

## 1. 전체 파이프라인 개요

```
[NEW] 0. 자연어 인테이크 (LLM, 추출 전용)
        └─> 구조화 트리거 JSON (기존 체크박스 폼과 동일 스키마)

1. Info Extractor (코드) ─ pass-through + PII 마스킹 + scope gate + week/phase 정합성
        │
        ├─ unsupported_surgery ──────────────► 종료 (리포트 없음)
        ├─ manual_review_required(동반술식) ──► 종료 (리포트 없음)
        │
2. Red-flag 사전 체크 (코드) ── pain_nrs>=4 OR swelling=true
        │
        ├─ 해당 시 ────────────────────────► PT 위임 (SOAP은 정상 생성, 운동 0개)
        │
3. Notes Screening (LLM, 이진 신호만)
        │
        ├─ concern=true ──────────────────► PT 위임 (SOAP은 정상 생성, 운동 0개)
        │
4. Retrieve (코드) ── phase/graft 조건으로 후보 최대 10개 결정론적 필터
        │
5. Safety Judge - Gate 1 (코드) ── rule_table 대조
        │
        ├─ approved ──────────────────────► 6. Generate Rx
        ├─ rejected_loop(1~10건 위반) ─────► Corrector → 4번으로 재검색 (최대 5회)
        └─ failed(11건 이상 위반) ─────────► 종료 (수동 검토)
        │
6. Generate Rx (코드) ── 안전 통과 풀에서 해시 시드 기반 N개 선택 (현재 N=3)
        │
7. Safety Judge - Gate 1' completeness (코드) ── 최종 N개 재검증 + 필수 필드 확인
        │
8. Reporter (LLM, 서술 전용) ── SOAP 4개 섹션만 이중언어로 생성
        │
9. Report Validate - Gate 3 (코드) ── 스키마/개수/필드/길이 기계 검증
        │
10. Report Judge - Gate 2 (LLM, 독립 검수) ── 서술 품질(J1) + groundedness(J4)만 판단
        │
        └─ 실패 시 8번으로 최대 3회 재시도(사유 포함) → 최종 실패 시 수동 검토
```

---

## 2. [NEW] 0단계 — 자연어 인테이크 에이전트 (Timely 전용 신규 스킬)

기존 체크박스 폼이 만들어내던 것과 **완전히 동일한 구조화 JSON**을 자연어에서 뽑아내는
것이 유일한 목적이다. 이 스킬이 잘못 만들면 뒤 파이프라인 전체가 틀어지므로, "모르면
채우지 않는다"는 원칙이 가장 중요하다.

### 페르소나
```
당신은 재활의학과 처방 의뢰서(referral note)를 구조화하는 정보 추출 담당자입니다.
당신은 절대로 임상적 판단을 내리지 않습니다 — 텍스트에 명시적으로 드러난 사실만
추출합니다. 텍스트에 없는 값은 추측하지 말고 null로 남기세요. 특히 다음을 반드시
지키세요:
- 수치(주차, 나이, 통증 점수)는 텍스트에 숫자나 명확한 표현이 있을 때만 채운다.
  "최근에 수술했다" 같은 모호한 표현으로 주차를 추측하지 않는다.
- 재활 단계(phase)가 텍스트에 명시되어 있지 않으면 null로 둔다 — 주차만으로
  단계를 역산하는 것은 이후 결정론적 코드가 담당하므로 당신이 하지 않는다.
- "특이사항"란에 들어갈 내용과 구조화 필드로 뽑을 내용을 헷갈리지 않는다:
  이미 구조화 필드(수술명/주차/나이/통증/부종/동반술식)로 뽑은 내용은 notes에
  중복해서 넣지 않는다. 그 외 모든 자유서술(약물, 동반 질환, 감정 표현 등)은
  notes에 원문 그대로 넣는다 — 절대 요약하거나 해석하지 않는다.
```

### 출력 스키마 (기존 `PatientInput`/trigger 스키마와 완전히 동일해야 함)
```json
{
  "surgery": "ACL_RECON" | null,
  "week_post_op": number | null,
  "age": number | null,
  "concomitant_procedure": string | null,
  "pain_nrs": number | null,
  "swelling": boolean | null,
  "notes": string,
  "surgery_details": {
    "phase": "PHASE_I" | "PHASE_II" | "PHASE_III" | "PHASE_IV" | "PHASE_V" | null,
    "graft_type": "hamstring_autograft" | null
  },
  "extraction_confidence": {
    "missing_required": string[],
    "ambiguous_fields": string[]
  }
}
```

### Fail-closed 규칙 (신규 게이트 — 기존엔 폼이 required로 강제했던 부분)
- `REQUIRED = [surgery, week_post_op, age, swelling, notes, surgery_details]` 중
  하나라도 null이면 하네스로 넘기지 말고 **"추가 정보 필요"** 응답으로 사용자(또는
  의뢰 작성자)에게 되물어야 한다. 절대 기본값(예: week_post_op=0)으로 채워서
  넘기지 않는다 — 이건 §4-A 데이터 바운드 원칙의 연장이다.
- `surgery`가 텍스트상 ACL 재건이 아닌 게 명백하면(예: "회전근개 봉합") 그대로
  통과시켜서 1단계(Info Extractor)의 GATE-01이 정상적으로 `unsupported_surgery`로
  처리하게 한다 — 여기서 임의로 막지 않는다.
- `phase`가 텍스트에 없으면 null로 두고 통과시킨다. 1단계의 `effective_phase()`
  로직이 `week_post_op` 기준으로 유도하므로 phase 자체는 필수가 아니다(단,
  week_post_op은 필수).

### 예시
| 자연어 입력 | 추출 결과 |
|---|---|
| "45세 환자, ACL 재건(슬건 자가건) 후 8주차, 통증 NRS 2, 부종 없음. 특이사항 없음." | surgery=ACL_RECON, week_post_op=8, age=45, graft_type=hamstring_autograft, pain_nrs=2, swelling=false, notes="" |
| "환자가 와파린 복용 중이라고 함. 나머지는 이전과 동일, 12주차." | week_post_op=12, notes="와파린 복용 중", 나머지는 null → **missing_required로 되물어야 함** (age, swelling 등 명시 안 됨) |
| "발목인대 손상도 있음" 같은 표현 | 구조화 필드로 뽑을 게 아니므로 그대로 notes에 원문 보존. 이 내용의 위험 판단은 이후 3단계(Notes Screening)가 함 — 여기서 판단하지 않는다. |

---

## 3. 1단계 — Info Extractor (코드, 결정론)

**LLM 아님.** Timely에서도 이 부분은 "코드 실행" 노드(함수/스크립트 실행)로 넣어야
하며, LLM 프롬프트로 대체하면 안 된다 (재현성 원칙 위반).

역할:
1. 구조화 필드 그대로 통과 (재해석 금지)
2. `notes` 정규식 마스킹 — LLM에 원문이 닿기 **전에** 실행:
   - 주민등록번호: `\d{6}-\d{7}`
   - 전화번호: 휴대폰/지역번호 패턴
   - 기관명: `(병원|의원|정형외과|재활의학과|한방병원|한의원|클리닉|보건소|센터)` 접미
   - 이름: `성+이름+호칭(님/씨/환자분/어르신)` 패턴 (호칭 없는 이름은 못 잡음 — 알려진 한계)
3. `age → age_band` (10년 단위, 예: 45 → "40s")
4. Scope gate:
   - `surgery != ACL_RECON` → `unsupported_surgery` (종료, 리포트 없음)
   - `concomitant_procedure is not null` → `manual_review_required` (종료, 리포트 없음)
5. week↔phase 정합성: `week_post_op`에서 유도한 phase와 선언된 phase 중 **더 낮은 쪽**을
   채택 (보수적 원칙) + `phase_week_mismatch` 플래그 기록

week/phase 매핑 테이블:
| Phase | 주차 범위 |
|---|---|
| PHASE_I | 0–2주 |
| PHASE_II | 3–6주 |
| PHASE_III | 7–12주 |
| PHASE_IV | 13–24주 |
| PHASE_V | 25주~ |

출력(내부 컨텍스트 객체, 이후 모든 단계가 공유):
```json
{
  "surgery": "ACL_RECON",
  "week_post_op": 8,
  "phase": "PHASE_III",              // 유효 phase (보수 채택 결과)
  "phase_declared": "PHASE_III",
  "phase_derived_from_week": "PHASE_III",
  "graft_type": "hamstring_autograft",
  "pain_nrs": 2,
  "swelling": false,
  "concomitant_procedure": null,
  "age_band": "40s",
  "notes_redacted": "...",
  "flags": {
    "unsupported_surgery": false,
    "manual_review_required": false,
    "manual_review_reason": null,
    "phase_week_mismatch": false,
    "red_flag": false
  }
}
```

---

## 4. 2단계 — Red-flag 사전 체크 (코드, 결정론)

**LLM 아님.** `pain_nrs >= 4` 이거나 `swelling == true`이면, 운동 검색·판정 자체를
건너뛰고 바로 "PT 위임" 상태로 리포트 단계로 넘어간다. SOAP 서술(S/O/A)은 정상 생성
되고, Plan에서만 "운동 추천 보류 + 담당 PT가 직접 결정" 문구가 들어간다.

> 설계 배경: 예전엔 이 로직을 규칙표의 `REDFLAG-01`(통증/부종 → 등척성 강제 치환)
> 룰로 처리했는데, red-flag 조건에 걸리는 운동이 한 번에 여러 개면 "위반 11건 이상 →
> 즉시 실패" 카운팅 임계값에 걸려서 교정 루프(치환 기회)조차 못 받고 죽는 버그가
> 있었다. 그래서 판정 루프에 들어가기 전에 여기서 먼저 걸러낸다. **Timely에서 구현할
> 때도 이 순서(판정 루프 진입 전에 컷)를 반드시 지켜야 한다.**

임계값: `PAIN_DEFER_THRESHOLD = 4` (NRS 4 이상)

---

## 5. 3단계 — Notes Screening (LLM, 이진 신호 전용)

**하지 않는 것**: "이 운동은 빼라/넣어라" 같은 판단. 안전 판정은 여전히 규칙표
대조(5단계)만 담당한다.

**하는 것**: `notes_redacted`에 "구조화된 필드로는 포착 안 되는, 재활 안전에 영향
줄 만한 내용"이 있는지 **이진값**으로만 판단.

### 페르소나 / 프롬프트
```
당신은 재활 운동처방 안전성 스크리닝 담당자입니다. 당신의 역할은 딱 하나,
"이 특이사항 텍스트 안에 구조화된 필드로는 알 수 없는, 재활 운동 안전성 판정에
영향을 줄 수 있는 내용이 있는가?"만 판단하는 것입니다. 절대 어떤 운동이 안전한지/
위험한지는 판단하지 마세요 — 그건 결정론적 규칙 엔진이 처리합니다.

이미 구조화된 필드로 별도 처리되므로 신경 쓰지 않아도 되는 것: 수술명, 회복 주차,
이식건 종류, 통증 수준(NRS), 부종 여부, 동반 수술 여부.

플래그를 켜야 하는 예: 복용 중인 약물(특히 항응고제·스테로이드·면역억제제), 유전
질환·결합조직 질환(예: 엘러스-단로스 증후군), 이번 수술과 무관한 다른 부위의
부상·질환(예: 발목 인대 손상, 허리 디스크), 선천적 신체 구조 이상, 임신 여부,
그 외 일반적인 재활 계획을 바꿀 만한 의학적 사실.

플래그를 켜면 안 되는 예: 단순 감정 표현("무섭다", "빨리 낫고 싶다"), 이미 구조화
필드로 들어온 내용의 반복(통증/부종 재언급), 안전과 무관한 일상 서술, 빈 내용.

반드시 아래 JSON 스키마 하나만 출력하라:
{"concern": true 또는 false, "reason": "왜 그렇게 판단했는지 한 줄", "quote": "해당 원문 일부 또는 빈 문자열"}
```

### Fail-safe 정책
- `notes`가 비어있으면 LLM 호출 없이 `concern=False` 즉시 통과 (비용/지연 절약)
- LLM 호출 자체가 실패하면 **안전 쪽으로** `concern=True` 처리 (확인 못 했으니 사람이 봐야 함)
- `concern=true` → 무조건 PT 위임(운동 0개, SOAP은 정상 생성) — 이 결과 동작은 항상
  고정이므로 LLM 표현이 매번 달라도 재현성이 깨지지 않음

---

## 6. 4단계 — Retrieve / 후보 검색 (코드, 결정론)

**LLM 아님.** 운동 라이브러리에서 `phase`가 일치하고 `source`가 있는 항목만 필터.
`priority`(낮을수록 우선) → `phase_dist`(현재 단계에 막 도입된 운동 우선) → 이름
순으로 정렬 후 **최대 10개**만 취한다. 교정 패스(재검색)가 있으면 그 필터(제외/속성
제한/등척성 강제)를 먼저 적용한다. 후보가 5개 미만이면 `insufficient_evidence`로
종료(운동을 지어내지 않음).

---

## 7. 5단계 — Safety Judge (Gate 1, 코드, 결정론) — 하네스의 핵심

**LLM 아님. 이 시스템에서 가장 중요한 결정론 지점.** 후보 각각을 규칙표(rule table)
와 대조한다.

### 판정 정책
- `hard_violations` = 발동된 (운동 × hard 룰) 쌍의 개수 (soft/input_gate 제외)
- `0건` → `approved` → 6단계로
- `1~10건` → `rejected_loop` → Corrector 실행 후 4단계부터 재시도 (최대 5회)
- `11건 이상` (전체 룰 수의 절반, 고정값) → `failed` → 수동 검토로 종료
- 반복 5회 초과 → `failed`로 강등

### 조건 매칭 문법 (`patient_if` / `exercise_if`)
```json
{"field": "week_post_op", "op": "lt", "value": 12}
{"all": [{"field": "pain_nrs", "op": "gte", "value": 5}, {"field": "pain_nrs", "op": "lte", "value": 6}]}
{"any": [...]}
```
지원 연산자: `eq, ne, in, gte, lte, gt, lt, is_null, not_null`. 빈 조건 `{}`는 항상 참.
`field`는 점 표기(`surgery_details.phase`)로 중첩 접근 가능.

### 현재 규칙표 전체 (20개, SAMPLE — 실제 임상 프로토콜 원문 대조 필요)

| rule_id | mode | severity | 내용 |
|---|---|---|---|
| GATE-01 | input_gate | hard | `surgery != ACL_RECON` → `unsupported_case` |
| GATE-02 | input_gate | hard | `concomitant_procedure not_null` → `manual_review_required` |
| GATE-03 | input_gate | hard | `graft_type != hamstring_autograft` → `unsupported_case` |
| REDFLAG-02 | safety | soft | 중등도 통증(NRS 5–6) → manual_review만 (카운트 제외) ⚠️ 현재 2단계의 pain≥4 사전 컷과 겹쳐 사실상 도달 불가 — 포팅 시 정리 필요 |
| HS-01 | safety | hard | PHASE I–II + 고부하 햄스트링 로딩 금지 (공여부 보호) |
| HS-02 | safety | hard | 12주 미만 + 저항성 무릎 굴곡 금지 (공여부) |
| HS-03 | safety | hard | 6주 미만 + 공격적 햄스트링 스트레칭 금지 |
| HS-04 | safety | hard | PHASE I–II + 원심성 햄스트링 운동 금지 |
| OKC-01 | safety | hard | PHASE I–II + 개방사슬 저항성 신전 금지 (이식건 전단부하) |
| OKC-02 | safety | hard | PHASE III OKC 신전은 90–40° 범위로 제한 (clamp) |
| ROM-01 | safety | hard | PHASE I 무릎 굴곡 90° 초과 금지 |
| ROM-02 | safety | hard | PHASE II 무릎 굴곡 120° 초과 금지 |
| WB-01 | safety | hard | PHASE I 편측 동적 하중 금지 |
| WB-02 | safety | soft | PHASE II 편측 하중 → manual_review만 |
| PLYO-01 | safety | hard | 12주 미만 플라이오메트릭 금지 |
| RUN-01 | safety | hard | 12주 미만 러닝 금지 |
| RTS-01 | safety | soft | 복귀 판정(LSI 등 측정 기준) → manual_review만 |
| DOS-01 | safety | hard | PHASE I–II 고강도(`intensity_level=high`) 처방 금지 |
| GEN-01 | safety | hard | 출처(source) 없는 후보 금지 |
| COMP-02 | completeness | hard | 최종 처방에 rationale/source 누락 금지 |

> 과거엔 `DOS-02`(dosage 라이브러리 값 일치), `COMP-01`(sets/reps/frequency/intensity
> 필수) 룰이 있었는데, dosage를 시스템이 정하지 않기로 하면서 제거함. `REDFLAG-01`
> (통증/부종 → 등척성 강제 치환) 룰도 2단계 사전 컷으로 대체되어 제거함.

### hard 룰의 `correction_hint` 예시 (Corrector가 그대로 소비)
```json
{
  "action": "exclude",
  "alternative_filter": {"hamstring_load_in": ["none", "low"]}
}
```
`action`은 `exclude`(제외 + 대체 필터 병합) / `clamp`(속성 상한·하한 수정, 제외 아님)
/ `force_isometric`(모든 동적 운동을 등척성으로 강제 치환) 셋 중 하나.

---

## 8. 6단계 — Corrector (코드, 결정론)

`rejected_loop`일 때만 실행. 위반 목록의 `correction_hint`를 기계적으로 병합해 다음
재검색 제약(`exclude`, `add_filters`, `clamps`, `force_isometric`)을 만든다. 같은
속성 키에 힌트가 여러 번 오면 **룰 순서가 고정**이므로 마지막 힌트가 결정론적으로
우선한다. 이후 4단계(Retrieve)로 돌아가 반복.

---

## 9. 7단계 — Generate Rx / 처방 조립 (코드, 결정론) — 다양성 로직

**LLM 아님. 생성이 아니라 "조립"이다.** 안전 통과(`safety_checked=true`) 후보 풀
(최대 10개)에서 **N개**(현재 N=3, 과거엔 5)를 골라 `rationale`/`source`를 라이브러리
값 그대로 복사한다.

### 선택 알고리즘 (해시 시드 기반 결정론적 의사난수 조합)
```python
def _selection_seed(ctx):
    key = "|".join(str(ctx.get(k)) for k in
        ("week_post_op", "phase", "graft_type", "pain_nrs", "swelling", "age_band"))
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)

rng = random.Random(_selection_seed(ctx))
selected = rng.sample(pool, N)
selected.sort(key=lambda e: e["name"]["en"])  # 표시 순서만 고정, 선택 자체는 이미 끝남
```
- 시드는 **구조화 필드만** 사용 (notes 등 자유 텍스트는 절대 사용 안 함 — §4-C 유지)
- 같은 환자(동일 구조화 값) → 항상 같은 시드 → 항상 같은 N개 (재현성)
- 다른 환자 → 다른 시드 → 후보 풀 안에서 다른 조합 (획일적 상위 N개 고정 방지)
- 안전 판정과는 무관 — 애초에 pool에 안전하지 않은 운동은 들어오지 않음
- **주의**: 후보 풀 자체가 작으면(N=3 기준 PHASE_I은 라이브러리에 7개뿐) 조합 수가
  제한된다 (`nCk`). N을 줄이면 조합 수(`C(pool, N)`)가 늘어나 다양성이 커진다 —
  실제로 5→3으로 낮췄더니 초기 단계에서도 조합이 겹치지 않는 걸 확인함.
- 후보가 N개 미만이면 재검색 필요 신호로 처리(운동을 지어내지 않음).

---

## 10. 8단계 — Reporter (LLM, 서술 전용)

**LLM에게 전체 JSON을 맡기지 않는다.** `exercises`/`report_meta`/`manual_review`/
`safety`는 파이썬(코드)이 그대로 조립하고, LLM은 **S/O/A/P 서술 문장(이중언어)만**
짧은 JSON으로 반환한다. 이러면 "처방을 절대 변형하지 않는다"는 제약이 LLM의 지시
준수 여부에 기대지 않고 구조적으로 보장된다.

### 페르소나 / 프롬프트 골격
```
당신은 물리치료사를 위한 재활 운동처방 검수 리포트의 서술(narrative) 작성자입니다.
아래 데이터만 근거로 SOAP 노트의 4개 서술 섹션을 한국어+영어 이중언어로 작성하세요.
절대 하지 말 것: 진단 내리기, 단정적 지시("반드시 ~하세요"), 아래 데이터에 없는
내용 서술, 운동 이름/용량을 새로 만들거나 바꾸는 것(운동 목록은 이미 확정되어 있고
당신은 손대지 않습니다).

[환자 컨텍스트] 연령대 / 참고 메모(마스킹됨) / 수술 후 주차 / 유효 재활 단계
(선언값·주차 유래값 병기) / phase_week_mismatch / 이식건 / 통증 NRS / 부종 / red flag

[확정된 처방 운동 N개 — 이미 안전성 검증 통과, 그대로 인용만 할 것] 또는
[운동 처방] 없음 — PT 위임 케이스인 경우

작성 지침:
- subjective: 연령대 + 주호소(참고 메모 기반)만. 마스킹된 메모 외 내용 지어내지 말 것.
- objective: 주차/유효 단계/부종/통증/이식건 등 관찰 사실. phase_week_mismatch 시
  "주차와 선언된 단계가 불일치하여 보수적으로 낮은 단계를 채택했다"는 취지 명시.
- assessment: 재활 단계 판단 근거·주의사항·red flag 여부. 진단/단정 금지.
- plan_summary: (정상 케이스) 운동 계획 2~3문장 요약 / (PT 위임 케이스) 운동을
  추천하지 않았다는 사실과 사유, PT가 직접 결정해야 한다는 취지를 2~3문장으로 명시.
```

출력 스키마:
```json
{
  "subjective": {"ko": "...", "en": "..."},
  "objective": {"ko": "...", "en": "..."},
  "assessment": {"ko": "...", "en": "..."},
  "plan_summary": {"ko": "...", "en": "..."}
}
```

LLM 호출 실패 시: 결정론적 폴백 서술(같은 데이터로 템플릿 조립)로 대체 —
`SAFERX_STRICT_LLM=1`이면 예외를 그대로 올려 실패 처리.

### 처방 항목 조립 (코드, LLM 관여 없음)
```json
{
  "name": {"ko": "...", "en": "..."},
  "rationale": {"ko": "...", "en": "..."},
  "source": "Brigham",
  "safety_checked": true,
  "note": {"ko": "범위 제한: ...", "en": "clamped: ..."}   // clamp 적용된 경우만
}
```
+ 고정 `dosage_note`: "세트·반복·빈도는 담당 물리치료사가 환자 상태에 따라 결정합니다."

### `manual_review` 조립 규칙 (코드)
1. PT 위임 케이스면 `exercise_selection_deferred_redflag` 항목 (사유·원문 인용 포함)
2. completeness 단계에서 남은 soft 룰 위반들
3. **항상 마지막에 고정으로 추가**: `quadriceps_strength_criterion` — "대퇴사두근
   근력 등 실측 지표는 자동 판정 대상 아님, PT 수동 확인 필요". 이건 그 케이스의
   판정 결과가 아니라 **시스템 자체의 한계를 알리는 상시 디스클레이머**다. 실측(촉진·
   검사도구 필요)이 필요한 기준은 이 하네스가 원천적으로 판단할 수 없으므로 매
   리포트마다 무조건 포함시킨다.

---

## 11. 9단계 — Report Validate (Gate 3, 코드, 결정론)

**LLM 아님.** 리포트 JSON에 대한 기계적 검증:
- V-PARSE: JSON 파싱 가능
- V-SCHEMA: §5 필수 키·타입 존재
- V-J2: `exercises` 개수가 정확히 `0`(PT 위임) 또는 `N`(현재 3)
- V-J3: 각 운동에 `rationale`/`source` 존재 (dosage 필드는 검사 대상 아님)
- V-J5: 필수 서술 필드가 ko/en 모두 비어있지 않음
- V-J6: 서술 텍스트 총 길이 ≤ 3500자 (A4 1장 프록시)
- V-SAFE: `safety.final_gate_passed == true`, 전 운동 `safety_checked == true`

실패 시 실패 사유를 Reporter에게 넘겨 재작성 요청 (최대 3회 반복).

---

## 12. 10단계 — Report Judge (Gate 2, LLM, 독립 검수)

**안전성은 재판정하지 않는다** — 이미 코드로 확정된 것을 다시 판단하지 않고, 서술
품질(J1)과 groundedness(J4)만 본다.

### 페르소나 / 프롬프트
```
당신은 재활 운동처방 SOAP 리포트의 독립 검수자입니다. 이 리포트를 작성하지
않았습니다. 아래 두 가지만 판단하세요 — 안전성 판정은 이미 코드로 확정되었으니
재판단하지 마세요.

J1 — 서술 품질: S/O/A/P 각 서술이 형식적 placeholder가 아니라 실질적 내용을 담고
있고, 문맥(주차/단계/red flag 여부)과 내적으로 일치하며, 진단/단정적 지시가 아니라
"제안+근거" 톤을 유지하는가? 한국어와 영어가 같은 내용을 전달하는가?

J4 — Groundedness: 서술의 모든 주장이 제공된 데이터(context, prescription)에서
실제로 확인되는가? prescription에 없는 운동/수치/임상적 주장이 등장하지 않는가?
마스킹된 notes의 내용을 추론해서 서술하지 않았는가?

출력: {"pass": true|false, "failed_checks": ["J1"/"J4" 중 실패한 것], "notes": "..."}
```

LLM 실패 시 degraded 모드: Gate 3(기계 검증)만 통과한 상태로 `pass=true` 처리하되
`notes`에 "J1/J4 미평가"임을 명시 (안전 관련 판정이 아니므로 완전 차단하지 않음).

---

## 13. 데이터 스키마 요약

### 운동 라이브러리 (`exercise_library.json`, 현재 30개, SAMPLE)
핵심 필드: `exercise_id, name{ko,en}, phases[], min_phase, priority, category,
load_type, kinetic_chain, target_muscle, resisted, resisted_knee_flexion,
hamstring_load, eccentric_hamstring, knee_flexion_max, knee_extension_end(optional),
weight_bearing, intensity_level, rationale{ko,en}, source`.
`dosage`/`dosage_status`는 데이터엔 남아있지만 **현재 파이프라인은 읽지도 출력하지도
않음** (팀 결정: dosage는 PT 재량).

### 규칙표 (`rule_table.json`) 스키마
```json
{
  "rule_id": "HS-01",
  "mode": "input_gate | safety | completeness",
  "severity": "hard | soft",
  "title": "...",
  "patient_if": { "field": "...", "op": "...", "value": ... },
  "exercise_if": { ... },
  "correction_hint": { "action": "exclude|clamp|force_isometric", "...": "..." },
  "quote_ref": "출처 표기"
}
```

### week/phase 매핑 (`week_phase_map.json`)
PHASE_I 0–2주 / PHASE_II 3–6주 / PHASE_III 7–12주 / PHASE_IV 13–24주 / PHASE_V 25주~
(SAMPLE — 팀 프로토콜 확정 후 교체 필요)

---

## 14. 최종 출력 스키마 (SOAP 리포트, 이중언어)

```json
{
  "report_meta": {
    "record_id": "...",
    "surgery": "ACL_RECON",
    "week_post_op": 8,
    "phase": "PHASE_III",
    "graft_type": "hamstring_autograft",
    "format": "SOAP",
    "language": "ko-en",
    "protocol_source": {"name": "...", "url": null, "refs": ["Brigham", ...]},
    "generated_at": "ISO8601"
  },
  "soap": {
    "subjective": {"ko": "...", "en": "..."},
    "objective": {"ko": "...", "en": "..."},
    "assessment": {"ko": "...", "en": "..."},
    "plan": {
      "ko": "...", "en": "...",
      "dosage_note": {"ko": "...", "en": "..."},
      "exercises": [ {"name": {...}, "rationale": {...}, "source": "...", "safety_checked": true, "note": {...}?} ]
    }
  },
  "manual_review": [ {"item": "...", "note": {"ko": "...", "en": "..."}} ],
  "safety": {"final_gate_passed": true, "violations": []}
}
```

`exercises.length === 0`이면 PT 위임 케이스 — 프론트엔드는 이걸로 빨간 경고 배너
("🚨 레드플래그 — 직접 확인 요망")를 띄운다.

---

## 15. LLM 호출 공통 설정

- 모델: `solar-pro2` (Upstage Solar, OpenAI 호환)
- `temperature=0.0` 고정 (LLM 지점에서도 결정론성을 최대한 확보하기 위함 — 그래도
  완전한 재현은 보장 안 되므로 위 "이진 스크리닝 패턴"/"결과 상태 고정" 설계로 보완)
- 응답은 반드시 JSON 하나만, 코드펜스 제거 로직 필요
- base_url은 `/v1` → `/v1/solar`(legacy) 순으로 폴백

---

## 16. Timely 이식 시 체크리스트

- [ ] 0단계(자연어 인테이크)는 새로 만들어야 함 — 나머지는 기존 로직 그대로 이식
- [ ] "코드/결정론" 단계(1, 2, 4, 5, 6, 7, 9단계)는 Timely의 로직/함수 실행 노드로
      구현하고, 절대 LLM 프롬프트 노드로 대체하지 않는다
- [ ] "LLM" 단계(0, 3, 8, 10단계)는 반드시 위에 명시된 페르소나·출력 스키마·이진/구조
      제약을 그대로 유지한다
- [ ] rule_table.json / exercise_library.json / week_phase_map.json은 데이터로
      그대로 이식(현재 SAMPLE 데이터라 실제 서비스 전 팀 프로토콜 원문 대조 필수)
- [ ] REDFLAG-02가 2단계 사전 컷과 겹쳐 도달 불가능해진 상태 — 포팅 시 정리할지
      결정 필요
- [ ] 재현성 검증: 동일 자연어 입력 3회 실행 → 0/1/2/4/5/6/7/9단계 산출물이 완전히
      동일한지 확인 (0/3/8/10단계의 LLM 표현 차이는 무관, 상태 전이만 같으면 됨)
