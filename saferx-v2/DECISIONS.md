# DECISIONS.md — spec 모호/미결 사항의 구현 결정

spec.md는 원본 그대로 유지했다. 아래는 spec이 열어둔 지점에 대해 이 구현이 택한
정의들이다. **팀 확정 시 spec에 반영하고 이 문서를 갱신할 것.**

## 1. hard_violations 카운트 단위 (spec §6-1 모호)
**결정: FIRE된 (운동 × hard 룰) 쌍의 개수.**
- soft 룰과 input_gate는 카운트 제외 (spec 명시대로).
- 임계값 0 / 1–10 / ≥11은 spec 고정값 유지.
- 알려진 한계: 후보 풀 크기에 따라 카운트 스케일이 달라짐. "나쁜 후보 풀"과
  "위험한 케이스"를 하나의 카운터로 판정하는 구조 자체는 spec 설계이므로 유지하되,
  운동별 `safety_checked` 필드로 개별 배제 정보도 함께 기록한다.

## 2. week→phase 매핑 (spec §4-G "팀 결정 필요")
**잠정: I=0–2주, II=3–6주, III=7–12주, IV=13–24주, V=25주+** (`data/week_phase_map.json`)
- "낮은 단계"의 정의: `min(선언 phase, 주차 유래 phase)` — phase_order 인덱스 기준.
- ⚠️ 팀 프로토콜 확정 전까지 잠정치.

## 3. "A4 1장" 길이 예산 (spec §4-H/§6-2 J6 — 기계 판정 불가 기준)
**결정: SOAP 서술 텍스트 총합 ≤ 3,500자를 프록시로 사용** (`report_validate.py`).
- 렌더링 환경이 확정되면 실측 기반으로 조정.

## 4. red flag 처리 경로 (spec §4-D)
**결정: 초기 검색은 red flag를 선필터하지 않는다.**
- spec의 설계("동적 운동 auto-fail → corrector 강제 치환")를 그대로 구현 —
  판정·교정이 로그로 남아 관측 가능하다.
- 대안(검색 단계 선필터)은 루프를 생략해 더 빠르지만 §4-D의 판정 경로가
  기록되지 않음. 프로덕션에서 선필터 + 판정 병행(이중 방어)으로 바꿔도 무방.

## 5. dosage gap 봉합 (원 설계의 검증 공백)
원 설계에서는 Gate 1이 *운동 이름*만 검사하고 generator가 붙인 용량은 검증되지
않았다. 두 겹으로 봉합:
- **generate_rx.py는 라이브러리 값을 복사만 한다** (생성·변형 금지, §4-A의 기계적 보장).
- **completeness 모드가 최종 5개에 대해 (a) 안전 룰 재평가 + (b) DOS-02
  (용량이 라이브러리 원본 초과 시 fail)를 수행한다.** → 변조·초과가 코드로 잡힘.

## 6. §4-F redaction의 자기모순 해소
원 설계는 "LLM 전달 전 마스킹"을 LLM 서브에이전트에 맡겼다(마스킹하려면 원문을
그 LLM이 봐야 하는 모순). **redaction을 `extract_redact.py`의 정규식 코드로 이관** —
LLM(리포터/저지)에는 `notes_redacted`와 `age_band`만 노출된다.
- 알려진 한계: 이름 마스킹은 "성+이름+호칭" 보수 패턴만 잡는다. 호칭 없는 이름,
  영문 이름은 미탐. 프로덕션에서는 한국어 NER 보강 필요.

## 7. 아키텍처: 서브에이전트 8개 → LLM 역할 3개
| 원 구성 (LLM) | v2 구성 |
|---|---|
| info-extractor-subagent | `scripts/extract_redact.py` (코드) |
| rag-recommender-subagent | `scripts/retrieve.py` (코드) |
| safety-judge-subagent | `scripts/safety_judge.py` (코드) — "스크립트 실행 후 중계"라던 LLM 래퍼 제거 |
| corrector-subagent | `scripts/correct.py` (코드) |
| generator-subagent | `scripts/generate_rx.py` (코드) |
| (없었음) | `scripts/report_validate.py` (코드) — Gate 3 + 기계적 J2/J3/J5/J6 이관 |
| reporter-subagent | **유지 (LLM)** — 서술 생성은 언어 작업 |
| report-judge-subagent | **유지 (LLM)** — 단 J1(서술 품질)·J4(groundedness)만 담당 |
| acl-safety-orchestrator | **유지 (LLM)** — 흐름 제어 + 스크립트 실행 |

근거: spec §6-1(결정론), §5 Reproducibility. 결정론 구간이 넓어질수록 재현성
보장 범위가 넓어진다. 실측: 동일 입력 2회 실행 시 판정·처방 바이트 동일 확인.

## 8. 샘플 데이터 경고
`rule_table.json`의 룰 조건·수치와 `exercise_library.json`의 운동·용량·출처는
표준 ACL 햄스트링 프로토콜을 참조한 **자리표시자(SAMPLE)**다. 임상 사용 전
반드시 팀 보유 프로토콜 원문과 대조·검증하고 source를 실제 문서 참조로 교체할 것.

## 9. 모델 배정: 판단·생성 = Solar Pro / 일반 = Solar
| 역할 | 성격 | 모델 |
|---|---|---|
| acl-safety-orchestrator | 일반 (흐름 제어 — 상태 코드 해석·스크립트 실행·재시도 예산 관리) | `solar` |
| reporter-subagent | **생성** (이중언어 SOAP 서술) | `solar-pro` |
| report-judge-subagent | **판단** (J1 서술 품질 · J4 groundedness 심사) | `solar-pro` |

- 원칙: 언어적 판단·생성 품질이 결과 품질을 좌우하는 역할에만 상위 모델을 쓴다.
  오케스트레이터는 임상·안전 판단 권한이 0이고 상태 분기만 하므로 일반 모델로 충분.
- Gate 1(안전 판정)은 모델과 무관 — 코드(`safety_judge.py`)이므로 어떤 모델
  배정에도 영향받지 않는다. 모델 교체가 안전 판정 재현성을 깨지 않는 것이
  이 아키텍처의 장점.
- ⚠️ `solar` / `solar-pro`는 사용자 지정 표기. 실제 Upstage API 모델 스트링
  (예: solar-pro2, solar-mini 등 시점별 명칭)은 하네스 연결 시 확인·치환할 것.
- 향후 thin-executor 에이전트를 추가하는 경우(§7 참고): 판단하지 않는
  실행자이므로 전부 `solar`(일반) 배정.

## 10. ChromaDB(Chroma Cloud) 통합 방식 — 근거 컨텍스트, 후보 선택 아님
- 컬렉션(`rehab_protocols`)은 운동 항목이 아니라 **프로토콜 텍스트 청크 6개**
  (KNEE 단일 조건)이며 정량값이 비구조화다 (가이드 §2/§5). 따라서 **후보 선택과
  안전 판정은 계속 exercise_library.json + rule_table.json이 담당**하고, Chroma는
  리포트의 protocol_source **근거 컨텍스트**(`work/05_protocol_context.json`)만
  공급한다 — 가이드 §5의 "규칙표 하드코딩이 재현성에 안전" 권고와 일치.
- 기본 조회 모드 = **metadata `get()` + 결정론적 phase 선별** (임베딩 불필요):
  현재 phase 본문 + 다음 phase 진입 기준 + week 범위 매치. 같은 입력 → 같은
  청크 (재현성 실측 확인). 시맨틱 검색(--semantic)은 UPSTAGE_API_KEY가 있을 때의
  탐색·디버깅용 선택 모드이며 파이프라인 기본 경로가 아니다 (가이드 §4의 동일
  임베딩 계열 제약도 이렇게 회피).
- 연결 분기: `rag/chroma_client.py` — CHROMA_API_KEY 있으면 Cloud
  (tenant/database는 가이드 §1 값), 없으면 로컬 `rag/chroma_db` (가이드 §6 계약).
- 실패는 **non-fatal**: Chroma 접근 불가 시 available:false 기록 후 파이프라인
  계속 (근거 컨텍스트는 보강재).
- 보안: API 키는 `rag/.env`에만 보관 (.gitignore 처리). **이 키는 채팅으로 공유된
  이력이 있으므로 Chroma Cloud 콘솔에서 로테이션할 것.**
- 검증 환경 주의: 개발 샌드박스는 api.trychroma.com 이그레스가 차단되어 Cloud
  연결의 실연동 확인은 사용자 환경에서 수행해야 한다. 로컬 모드로 스키마 동일
  시드 후 선별 로직·재현성은 검증 완료.

## 11. 환자 페르소나(patients_soap_30.csv) → 트리거 입력 매핑
30명 페르소나를 테스트 스위트로 채택 (`samples/personas/`, 변환기:
`scripts/convert_personas.py`). CSV의 SOAP 서술형 필드를 스키마로 옮기는 규칙:
- `surgery`: ACL_HS → ACL_RECON, 그 외(THA_POST/RCR_ARTHRO/ACH_REPAIR)는 원문
  유지 → GATE-01의 unsupported_surgery 검증용 (21명).
- `week_post_op`: floor(post_op_weeks) — 소수 주차 내림 (보수 방향, §4-G와 일치).
- `pain_nrs`: O_objective의 "NRS n/10" 정규식 추출.
- `swelling`(bool): 부종 없음/경미 → false, **중등도/심함/증가 → true**.
  ⚠️ '경미=false' 경계는 팀 확인 필요 — true로 바꾸면 P002 등도 red flag 경로.
- `concomitant_procedure`: surgical_flags none → null, 그 외 원문
  (P009 meniscal_repair → §4-E manual review 검증).
- `phase`: expected_phase 로마자 매핑, enum 밖("VI")은 PHASE_V 클램프
  (해당 행은 스코프 밖 수술이라 무해).
- `notes`: S_subjective(환자 보고) 원문.
배치 결과 (`scripts/run_batch.py`): **30/30 기대 상태 일치** —
ready 8(ACL) / manual_review 1(P009) / unsupported 21. red flag 2건(P001·P003)은
교정 루프(iter 2)로 전량 등척성 치환, 트랩 케이스(P005 러닝 요구 등)에서
금기 운동 미포함 확인.

## 12. 팀 제작 운동 데이터로 교체 (exercise_movement_map.csv + sources.csv)
- `data/exercise_library.json`을 팀 데이터 30개(ACL-HS-EX-v2-team)로 교체.
  이전 SAMPLE은 `data/legacy/`에 보존. 변환기: `scripts/build_library.py`
  (CSV 갱신 시 재실행). 원본 CSV는 더블 인코딩(UTF-8→mac_roman) 복구본을
  `data/exercise_movement_map.csv`로 보존. 출처 상세: `data/sources.json`
  (Escamilla 2012 · Wilk 1996 · Brigham protocol[미검증 verified=N] · curated).
- **min_phase 모델**: phases = [min_phase..V] (해당 단계부터 허용). 이에 맞춰
  검색 정렬을 phase-distance 우선(현 단계 도입 운동 먼저)으로 바꾸고,
  generate_rx가 priority로 재정렬하던 버그를 수정(검색 순서 보존).
- **룰 3건을 팀 데이터 명세에 정렬**: HS-02 → week<12 저항성 무릎굴곡 금지
  (EX021 note "12주까지 금기"), HS-04 → PHASE I–II만 (EX023 경량 RDL을 팀이
  min_phase III로 큐레이션), OKC-02 → 90–40° (EX022 note).
- **파생 필드 규칙**은 build_library.py 상단 주석 참고. ⚠️ intensity_level은
  acl_strain_level 프록시(개념 상이 — 팀 확인), ⚠️ dosage는 원본에 없어 전 항목
  placeholder(sets/reps/frequency/intensity 팀 확정 필요, dosage_status 필드로 표시).
- **커버리지 공백 발견 (배치 28/30)**: PHASE_I 등척성 운동이 EX001 하나뿐이라
  red flag 케이스(P001·P003)에서 §4-D 전량 등척성 치환 시 5개를 못 채워
  insufficient_evidence로 에스컬레이션됨. 파이프라인의 정직한 폴백이며 버그
  아님. 해소하려면 팀이 CSV에 초기 등척성 운동 추가 필요
  (후보 예: 둔근 세트, 내전근 볼 스퀴즈, 고관절 외전 등척성, 다각도 대퇴사두근
  등척성 — legacy 라이브러리 참고). 추가 후 `build_library.py` 재실행.
- 미결: EX011 note "규칙표서 90-30 제한"(레그프레스), EX026 note "6-9개월
  제한"(현재 min_phase IV=13주 시작과 간극) — 룰 추가 여부는 룰 수 22 고정
  (spec 임계값 절반=11)과 함께 팀 결정 필요.
