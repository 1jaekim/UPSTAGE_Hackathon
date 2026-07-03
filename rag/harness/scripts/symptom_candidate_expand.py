"""symptom_candidate_expand.py — 특이사항 기반 후보 발굴 보강 (RAG + LLM, 폐쇄형).

역할: notes_redacted를 ChromaDB(rehab_protocols, 프로토콜 PDF 임베딩)와 유사도 검색해
관련 프로토콜 문단을 찾고, 그 문단이 "라이브러리에 이미 있는 30개 운동 중" 어떤 것과
관련 있는지 LLM에게 묻는다. 결과는 retrieve.py의 후보 정렬 우선순위에만 반영되고,
안전 판정(safety_judge.py)은 그대로 전부 다시 거친다 — 이 스킬은 안전 게이트를
우회하지 않는다.

안전장치:
  - 출력은 exercise_library.json에 실제 존재하는 exercise_id로만 제한(폐쇄 집합).
    목록 밖 이름을 LLM이 만들어내면 그 항목은 버린다 (§4-A 데이터 바운드 원칙).
  - notes_redacted가 비어있으면 임베딩/LLM 호출 없이 즉시 빈 결과로 통과.
  - 임베딩/ChromaDB/LLM 중 하나라도 실패하면 빈 결과로 안전하게 폴백한다 —
    이 스킬은 "있으면 좋은 보강"이지 필수 경로가 아니므로 실패해도 파이프라인은 안 죽는다.
  - 재현성: notes_redacted + 구조화 필드(phase/week/graft_type) 해시로 결과를
    data/symptom_expand_cache.json에 캐싱한다. 같은 입력은 항상 같은 캐시를 재생하므로
    임베딩/LLM의 미세한 비결정성이 최종 처방에 영향을 주지 않는다.

usage: python3 symptom_candidate_expand.py
"""
import hashlib
import json
import os
import sys

from lib import load_json, save_json, work_path, DATA, ROOT

RAG_ROOT = os.path.dirname(ROOT)  # rag/
sys.path.insert(0, RAG_ROOT)

CACHE_PATH = os.path.join(DATA, "symptom_expand_cache.json")
TOP_K = 5


def _cache_key(notes, ctx):
    key = "|".join([notes, str(ctx.get("phase")), str(ctx.get("week_post_op")),
                     str(ctx.get("graft_type"))])
    return hashlib.sha256(key.encode()).hexdigest()


def _load_cache():
    if os.path.exists(CACHE_PATH):
        return load_json(CACHE_PATH)
    return {}


def _save_cache(cache):
    save_json(CACHE_PATH, cache)


def _embed_query(text):
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv(os.path.join(RAG_ROOT, ".env"))
    client = OpenAI(api_key=os.environ["UPSTAGE_API_KEY"], base_url="https://api.upstage.ai/v1/solar")
    resp = client.embeddings.create(model="embedding-query", input=[text])
    return resp.data[0].embedding


def _query_protocols(embedding, k=TOP_K):
    from chroma_client import get_chroma_client
    collection = get_chroma_client().get_collection("rehab_protocols")
    result = collection.query(query_embeddings=[embedding], n_results=k, where={"condition": "KNEE"})
    return result["documents"][0] if result["documents"] else []


PROMPT_TMPL = """당신은 재활 프로토콜 문서 조각과 환자의 특이사항 메모를 보고, 아래 "허용된
운동 목록"에서만 관련 있는 운동을 고르는 담당자입니다. 절대 목록에 없는 운동 이름을
만들어내지 마세요. 이 판단은 최종 안전 승인이 아니라 "검토 우선순위 힌트"일 뿐이며,
당신이 고른 운동도 이후 별도의 결정론적 안전 규칙 검사를 그대로 통과해야 합니다.

[허용된 운동 목록 (exercise_id: 이름)]
{exercise_list}

[환자 특이사항 메모 (마스킹됨)]
{notes}

[관련 프로토콜 문서 조각들]
{passages}

위 문서 조각과 특이사항을 참고할 때, 허용된 목록 중 어떤 운동이 이 환자의 상황과
관련이 깊어 우선 검토할 만한가? 확신이 없으면 빈 배열을 반환하세요.

반드시 아래 JSON 스키마 하나만 출력하라(설명 문장 금지):
{{"exercise_ids": ["EX001", "EX003"] 형태의 배열, 관련 없으면 빈 배열}}
"""


def _llm_map_to_library(notes, passages, exercise_ids_and_names):
    from upstage_client import chat_json
    exercise_list = "\n".join(f"{eid}: {name}" for eid, name in exercise_ids_and_names)
    passages_block = "\n---\n".join(passages) if passages else "(검색된 문서 없음)"
    prompt = PROMPT_TMPL.format(exercise_list=exercise_list, notes=notes, passages=passages_block)
    result = chat_json(prompt)
    return result.get("exercise_ids", [])


def main():
    ctx = load_json(work_path("00_context.json"))
    notes = (ctx.get("notes_redacted") or "").strip()

    if not notes:
        save_json(work_path("07_symptom_expand.json"),
                   {"rag_exercise_ids": [], "cached": False, "reason": "notes 비어있음"})
        print("symptom_candidate_expand: notes 비어있음 -> 확장 없음")
        sys.exit(0)

    cache = _load_cache()
    key = _cache_key(notes, ctx)
    if key in cache:
        save_json(work_path("07_symptom_expand.json"), {**cache[key], "cached": True})
        print(f"symptom_candidate_expand: 캐시 히트 -> {cache[key]['rag_exercise_ids']}")
        sys.exit(0)

    lib = load_json(os.path.join(DATA, "exercise_library.json"))
    known_ids = {e["exercise_id"] for e in lib["exercises"]}
    id_name_pairs = [(e["exercise_id"], e["name"]["en"]) for e in lib["exercises"]]

    try:
        embedding = _embed_query(notes)
        passages = _query_protocols(embedding)
        raw_ids = _llm_map_to_library(notes, passages, id_name_pairs)
        validated_ids = sorted(set(i for i in raw_ids if i in known_ids))
        result = {"rag_exercise_ids": validated_ids, "cached": False}
    except Exception as e:
        print(f"[symptom_candidate_expand] 실패, 빈 결과로 폴백: {type(e).__name__}: {e}")
        result = {"rag_exercise_ids": [], "cached": False, "error": type(e).__name__}

    cache[key] = {k: v for k, v in result.items() if k != "cached"}
    _save_cache(cache)
    save_json(work_path("07_symptom_expand.json"), result)
    print(f"symptom_candidate_expand: rag_exercise_ids={result['rag_exercise_ids']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
