"""fetch_protocol.py — ChromaDB에서 프로토콜 근거 컨텍스트 조회 (코드).

용도: 후보 선택이 아니라 **리포트 근거(protocol_source) 컨텍스트** 공급.
후보 선택은 계속 exercise_library.json + rule_table.json이 담당한다 —
컬렉션은 텍스트 청크 6개뿐이고 정량값이 비구조화라(가이드 §5) 후보/판정용으로
부적합하며, 가이드 스스로 규칙표 하드코딩이 재현성에 안전하다고 권고한다.

기본 모드 = **metadata get (결정론)**: 임베딩 불필요.
  collection.get(where={"condition":"KNEE"})로 전체(6개)를 받아,
  section_title을 정규화("P HASE I" 공백 오염 대응)해 현재 phase 섹션 +
  다음 phase 진입 기준(criteria) 섹션을 결정론적으로 선별한다.
  → Upstage 임베딩 키 불필요, 같은 입력 → 같은 청크 (재현성 유지).

선택 모드 = semantic (--semantic): UPSTAGE_API_KEY 있을 때만.
  가이드 §4대로 embedding-query로 쿼리 임베딩 후 collection.query.
  탐색·디버깅용이며 파이프라인 기본 경로에는 쓰지 않는다.

실패는 non-fatal: Chroma 접근 불가 시 available:false로 기록하고 파이프라인은
계속 진행한다 (근거 컨텍스트는 보강재이지 필수 입력이 아님).

usage: python3 fetch_protocol.py [--semantic "query text"]
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import load_json, save_json, work_path, ROOT

ROMAN = {"PHASE_I": "I", "PHASE_II": "II", "PHASE_III": "III",
         "PHASE_IV": "IV", "PHASE_V": "V"}
NEXT = {"PHASE_I": "PHASE_II", "PHASE_II": "PHASE_III", "PHASE_III": "PHASE_IV",
        "PHASE_IV": "PHASE_V", "PHASE_V": None}


def title_has_phase(title, roman):
    """제목에서 PHASE {로마자}를 찾는다. 'P HASE I' 같은 글자 사이 공백 오염은
    허용하되(글자 간 \s*), 로마자 뒤 경계는 유지한다 — 공백을 전부 제거하면
    'Phase III include' → 'PHASEIIIINCLUDE'가 되어 III가 IIII로 오매칭된다."""
    t = (title or "").upper()
    for m in re.finditer(r"P\s*H\s*A\s*S\s*E\s*([IVX]+)(?![A-Z])", t):
        if m.group(1) == roman:
            return True
    return False


def pick_deterministic(records, phase, week):
    """현재 phase 본문 + 다음 phase 진입 기준 + (보조) week 범위 매치."""
    cur, nxt = ROMAN[phase], ROMAN.get(NEXT[phase]) if NEXT[phase] else None
    picked, seen = [], set()
    for r in records:
        t = r["metadata"].get("section_title", "")
        wmin, wmax = r["metadata"].get("week_min", -1), r["metadata"].get("week_max", -1)
        hit = title_has_phase(t, cur) or (nxt and title_has_phase(t, nxt)) \
              or (wmin != -1 and wmax != -1 and wmin <= week <= wmax)
        if hit and r["id"] not in seen:
            seen.add(r["id"])
            picked.append(r)
    picked.sort(key=lambda r: r["id"])  # 결정론적 순서
    return picked


def fetch_all_knee(collection):
    res = collection.get(where={"condition": "KNEE"},
                         include=["documents", "metadatas"])
    return [{"id": i, "metadata": m or {}, "document": d or ""}
            for i, m, d in zip(res["ids"], res["metadatas"], res["documents"])]


def main():
    ctx = load_json(work_path("00_context.json"))
    out = {"available": False, "mode": None, "reason": None, "chunks": []}
    try:
        sys.path.insert(0, os.path.join(ROOT, "rag"))
        from chroma_client import get_collection
        collection, conn = get_collection()

        if "--semantic" in sys.argv:
            # 선택 모드: Upstage embedding-query 필요 (가이드 §4 — 동일 임베딩 계열 필수)
            from chroma_client import load_env
            load_env()
            up_key = os.environ.get("UPSTAGE_API_KEY")
            if not up_key:
                raise RuntimeError("semantic 모드는 UPSTAGE_API_KEY 필요 (rag/.env)")
            from openai import OpenAI
            q = sys.argv[sys.argv.index("--semantic") + 1]
            ec = OpenAI(api_key=up_key, base_url="https://api.upstage.ai/v1/solar")
            emb = ec.embeddings.create(model="embedding-query", input=[q]).data[0].embedding
            res = collection.query(query_embeddings=[emb], n_results=3,
                                   where={"condition": "KNEE"})
            chunks = [{"id": i, "metadata": m, "document": d}
                      for i, m, d in zip(res["ids"][0], res["metadatas"][0], res["documents"][0])]
            out.update(available=True, mode=f"semantic/{conn}", chunks=chunks)
        else:
            # 기본 모드: 결정론적 metadata get
            records = fetch_all_knee(collection)
            picked = pick_deterministic(records, ctx["phase"], ctx["week_post_op"])
            out.update(available=True, mode=f"metadata_get/{conn}",
                       chunks=[{"id": r["id"],
                                "section_title": r["metadata"].get("section_title"),
                                "source_file": r["metadata"].get("source_file"),
                                "week_min": r["metadata"].get("week_min"),
                                "week_max": r["metadata"].get("week_max"),
                                "text": r["document"]} for r in picked])
    except Exception as e:
        out["reason"] = f"{type(e).__name__}: {e}"

    save_json(work_path("05_protocol_context.json"), out)
    if out["available"]:
        print(f"wrote work/05_protocol_context.json "
              f"({len(out['chunks'])} chunks, mode={out['mode']})")
    else:
        print(f"protocol context unavailable (non-fatal): {out['reason']}")


if __name__ == "__main__":
    main()
