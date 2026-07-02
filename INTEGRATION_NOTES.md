# 통합 노트 — demo-v1 프론트 ↔ SafeRx 하네스 (동작 확인 완료)

## 이번에 반영된 것
1. **데이터 최신화** (커밋 "운동,Judge 룰 매핑 x"의 미완 부분):
   - `rag/harness/data/exercise_library.json` → 팀 movement map 30개 (ACL-HS-EX-v2-team)
   - `rag/harness/data/rule_table.json` → 팀 데이터 정렬본 (HS-02 wk<12 / HS-04 I–II / OKC-02 90–40°)
   - `sources.json`·`exercise_movement_map.csv`·`sources.csv`·`build_library.py` 동봉 (CSV 수정 시 빌더 재실행)
2. **스크립트 최신화**: `retrieve.py` phase-distance 정렬(현 단계 도입 운동 우선),
   `generate_rx.py` 검색 순서 보존 (후기 단계 처방의 단계 적합성 버그 수정)
3. **LLM 폴백 (opt-in)**: `SAFERX_ALLOW_LLM_FALLBACK=1`일 때만 —
   reporter는 결정론적 이중언어 서술 템플릿, judge는 "DEGRADED (Gate 3 only)" 명시 통과.
   미설정(프로덕션 기본)이면 기존대로 엄격 실패.
4. `.env` 2개 생성 (둘 다 gitignore 됨):
   - `rag/.env`: UPSTAGE_API_KEY, CHROMA_API_KEY
   - `./.env`: VITE_HARNESS_ENDPOINT=http://127.0.0.1:8787/run-harness

## 실행 방법
```bash
# 백엔드 (rag/)
pip install fastapi uvicorn python-dotenv openai chromadb
cd rag && uvicorn hooks_server:app --host 0.0.0.0 --port 8787
# 프론트 (레포 루트)
npm install && npm run dev
```

## 검증 결과 (curl, 로컬)
| 시나리오 | status | 비고 |
|---|---|---|
| P002 정상 (PHASE_II) | ready_for_reporter | report 포함, 처방 5개 단계 적합 |
| P007 (PHASE_III) | ready_for_reporter | iterations=2, correction_used=true (OKC-02 clamp 루프) |
| P009 동반시술 | manual_review_required | detail=concomitant_procedure |
| TKA | unsupported_surgery | — |
| P001 red flag | insufficient_evidence | PHASE_I 등척성 1개뿐 (데이터 공백 — 아래) |
| P002 2회 반복 | 처방·판정 동일 | 재현성 ✓ |
| Wire 계약 | status/detail/correction_used/iterations/report + 이중언어 SOAP | 전부 적합 ✓ |

## 남은 항목
- **PHASE_I 등척성 운동 보강**: red flag 케이스가 5개를 못 채워 insufficient_evidence로
  에스컬레이션됨(정직한 폴백). CSV에 초기 등척성 추가 후 `build_library.py` 재실행.
- **dosage**: movement map에 없어 전 항목 placeholder — 팀 확정 필요.
- **LLM 실연동**: 이 검증은 폴백 모드였음(개발 샌드박스에서 api.upstage.ai 차단).
  네트워크 되는 환경에서 `SAFERX_ALLOW_LLM_FALLBACK` 없이 1회 확인 필요.
- **🔑 키 로테이션**: UPSTAGE·CHROMA 키 모두 채팅 공유 이력 있음 — 콘솔에서 재발급 권장.

## 트러블슈팅 — "실행 실패: Load failed"
브라우저의 fetch가 서버에 **연결 자체를 못 했다**는 뜻 (Safari: Load failed / Chrome: Failed to fetch).
점검 순서:
1. **백엔드가 떠 있는가**: 브라우저에서 `http://127.0.0.1:8787/health` 열기 →
   `{"status":"ok"}`가 나와야 함. 안 나오면 `cd rag && uvicorn hooks_server:app --host 0.0.0.0 --port 8787`.
2. **uvicorn이 뜨다가 죽는가**: 터미널 에러를 볼 것. 가장 흔한 원인은
   `ModuleNotFoundError: chromadb` — **Python 3.13+에서 chromadb 설치가 실패**하는 경우.
   → 이번 패치로 chromadb는 지연 import로 바뀌어 **없어도 /run-harness는 동작**함.
   `pip install fastapi uvicorn python-dotenv openai` 만으로 서버가 뜬다.
3. `.env`(VITE_HARNESS_ENDPOINT)를 바꿨다면 `npm run dev` 재시작 필요.
   미설정이어도 이제 기본값 `http://127.0.0.1:8787/run-harness`로 붙는다.
4. 그래도 실패하면 프론트 에러 메시지에 이제 점검 안내가 그대로 표시된다.

## 이번 수정 (Load failed 대응)
- `rag/hooks_server.py`: chromadb **지연 import** (로깅 훅에서만 로드), `GET /health` 추가,
  파이프라인 예외를 JSON `{detail}`로 반환.
- `src/api/harness.ts`: fetch 연결 실패 시 점검 방법이 담긴 한국어 에러 메시지,
  HTTP 오류 시 서버 detail 표시, 엔드포인트 기본값 내장.
- `rag/requirements.txt`: 필수/선택 구분 (chromadb는 선택).
