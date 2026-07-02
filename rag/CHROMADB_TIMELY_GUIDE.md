# ChromaDB (Chroma Cloud) 연동 가이드 — Timely Knowledge Base 블록용

이 문서는 Timely에서 RAG 추천 에이전트(Knowledge Base 블록)를 만들 때 필요한
ChromaDB 연결 정보와 데이터 스키마를 정리한 것. `harness_agent_spec` 2.2절
(RAG 추천 에이전트)과 짝을 이룬다.

## 1. 연결 정보

호스팅: **Chroma Cloud** (로컬이 아니라 클라우드에 떠 있어서 Timely에서 바로 접근 가능)

| 항목 | 값 |
|---|---|
| Tenant | `68a6db9d-c8a8-4f7c-879f-b5d843ecc7c4` |
| Database | `SpineSurgery2ThousandWon` |
| Collection | `rehab_protocols` |
| API Key | `rag/.env`의 `CHROMA_API_KEY` 참고 (문서에 원문 기재하지 않음) |

Python에서 연결하는 예:

```python
import chromadb

client = chromadb.CloudClient(
    api_key="<CHROMA_API_KEY>",
    tenant="68a6db9d-c8a8-4f7c-879f-b5d843ecc7c4",
    database="SpineSurgery2ThousandWon",
)
collection = client.get_collection("rehab_protocols")
```

Timely의 Knowledge Base 블록이 REST 엔드포인트 방식으로 붙는지, 전용 커넥터로
붙는지는 캔버스에서 직접 확인 필요. REST로 붙는다면 Chroma Cloud의 API
엔드포인트 + 위 tenant/database/api_key를 헤더/쿼리에 넣는 방식일 가능성이 높음.

## 2. 현재 적재 범위

**KNEE(ACL 재건, 슬건 자가이식) 단일 조건만 들어있음.** 원래 아킬레스건/고관절/
어깨 프로토콜도 시험 삼아 넣었다가, `harness_agent_spec` v3에서 스코프를 ACL
단일 수술로 확정하면서 나머지 3개는 삭제함. 컬렉션에는 `KNEE` 조건 문서 6개
섹션만 존재.

## 3. 문서(레코드) 스키마

컬렉션의 각 레코드는 ACL 재활 프로토콜 원문(`knee.pdf`)을 Phase 단위로 쪼갠
텍스트 청크 하나에 대응한다.

- **id**: `KNEE-0`, `KNEE-1`, … (파일 내 순서)
- **document** (본문 텍스트): `"{섹션 제목}\n{본문}"` 형태의 원문. 표는
  `레이블 | 값` 형태로 행 단위 변환되어 포함됨 (예: `Weight Bearing | NWB`).
- **metadata**:
  | 필드 | 타입 | 설명 |
  |---|---|---|
  | `condition` | string | 항상 `"KNEE"` |
  | `condition_label` | string | `"무릎"` |
  | `section_title` | string | Phase 제목 (예: `"P HASE I: Immediately post-operatively to week 4"`) |
  | `week_min` / `week_max` | int | 섹션 제목에서 정규식으로 추출한 주차 범위. 못 찾으면 `-1` (실제로 대부분의 하위 섹션에서 `-1`임 — 아래 "알려진 한계" 참고) |
  | `source_file` | string | `"knee.pdf"` |

현재 들어있는 6개 섹션 제목 예시:
- `Department of Rehabilitation ServicesPhysical Therapy` (문서 서두, 개요)
- `P HASE I: Immediately post-operatively to week 4`
- `Criteria for advancement to Phase II:`
- `Criteria to advance to Phase III include:`
- `Criteria for advancement to Phase IV:`
- `Criteria for advancement to Phase V:`

## 4. 임베딩 — 반드시 같은 모델로 조회할 것

문서는 **Upstage Solar Embedding API**의 `embedding-passage` 모델로 임베딩되어
들어가 있음 (`base_url: https://api.upstage.ai/v1/solar`). 쿼리(검색어)도 같은
Upstage Solar 계열의 `embedding-query` 모델로 임베딩해야 한다. 다른 임베딩
모델(OpenAI, 로컬 모델 등)로 쿼리하면 벡터 공간이 달라서 검색이 안 맞는다.

```python
from openai import OpenAI

embed_client = OpenAI(api_key="<UPSTAGE_API_KEY>", base_url="https://api.upstage.ai/v1/solar")
query_embedding = embed_client.embeddings.create(
    model="embedding-query", input=["2주차 ACL 재건 금기 동작"]
).data[0].embedding

result = collection.query(query_embeddings=[query_embedding], n_results=3, where={"condition": "KNEE"})
```

Timely의 Knowledge Base 블록이 자체 임베딩 모델을 강제한다면(예: 자체 OpenAI
임베딩만 지원), 이 컬렉션을 그대로 못 쓰고 그 모델로 재임베딩해서 새로
올려야 할 수 있음 — 블록 설정에서 임베딩 모델을 고를 수 있는지 먼저 확인.

## 5. 알려진 한계 (Judge/Corrector 설계 시 주의)

- `week_min`/`week_max`는 섹션 **제목 자체**에 주차가 명시된 경우만 채워진다.
  "Criteria for advancement to Phase II" 같은 제목은 주차가 없어서 `-1`.
  Judge가 "N주차 → 어떤 Phase" 매핑이 필요하다면, 이 필드에만 의존하지 말고
  본문 텍스트(`document`)에서 추가로 파싱하거나 별도 규칙표를 만들어야 함.
- ROM 상/하한, 체중부하(NWB/PWB/WBAT/FWB) 같은 정량 값은 메타데이터로
  구조화되어 있지 않고 본문 텍스트 안에 자연어/표 형태로만 존재함. Judge가
  이 값들을 정량 비교하려면, RAG가 반환한 텍스트에서 별도로 추출하는 단계가
  필요하거나, 이 문서를 참고해 사람이 직접 규칙표(JSON)를 만들어 Judge에
  하드코딩하는 편이 재현성 측면에서 더 안전함 (`harness_agent_spec` 2.3절의
  "결정론적이어야 한다" 원칙 참고).

## 6. 재적재/수정 방법

원본 스크립트는 `rag/ingest_protocols.py` (파싱+임베딩+적재),
`rag/query_protocols.py` (검색 테스트), `rag/chroma_client.py` (연결 분기:
`CHROMA_API_KEY`가 있으면 Chroma Cloud, 없으면 로컬 파일 `rag/chroma_db`).
문서를 다시 파싱하거나 청킹 로직을 바꾸고 싶으면 이 세 파일을 참고.
