---
name: rag-recommender
description: 현재 phase·이식건 조건에 맞는 후보 운동을 우리 데이터에서만 검색해야 할 때(초기 검색 및 교정 루프 재검색) 이 Skill을 사용한다.
---

## 목적 및 범위
`data/exercise_library.json`(프로덕션: ChromaDB)에서 phase·graft 적합 후보를 결정론적으로 검색한다.
결과물: `work/10_candidates.json` 1개 — 후보 최대 10개(각각 source 필수) + `insufficient_evidence` 플래그.
**실행 주체는 `scripts/retrieve.py`(코드)다.**

## 작업 절차
1. spec.md에서 범위(데이터 바운드)와 제약 [4-A]를 읽는다.
2. 실행: `python3 scripts/retrieve.py` — `work/00_context.json`에서 필터를 자동 구성하고, `work/30_correction.json`이 있으면 교정 제약(exclude/add_filters/clamps/force_isometric)을 적용한다.
3. exit code를 해석한다: `0` 계속 / `12` insufficient_evidence 종료.
4. 후보 수(≥5)와 전 항목 source 존재를 확인한다.

## 사용 규칙 및 제약 사항
- 데이터 밖 운동 생성 금지. 후보 부족 시 임의로 채우지 않고 `insufficient_evidence`를 반환한다 [4-A].
- 무출처 항목은 후보에서 제외된다.
- 정렬은 priority → name_en 고정 — 동일 입력이면 후보 목록·순서까지 동일해야 한다.
- 초기 검색은 red flag를 선필터하지 않는다 — [4-D]의 처리 경로(판정→교정 치환)를 관측 가능하게 유지한다 (DECISIONS.md #4).
- 프로덕션 교체 시 라이브러리 필터 함수만 ChromaDB 쿼리로 바꾸고 입출력 JSON 계약은 유지한다.

## 템플릿

```json
{
  "iteration": 1,
  "filters": { "phase": "PHASE_I", "graft_type": "hamstring_autograft" },
  "candidates": [
    { "name": { "ko": "대퇴사두근 등척성 수축", "en": "Quadriceps isometric set" },
      "source": "SAMPLE_PROTOCOL.pdf#p3", "priority": 1,
      "load_type": "isometric", "hamstring_load": "none", "knee_flexion_max": 0 }
  ],
  "candidate_count": 8,
  "insufficient_evidence": false
}
```
