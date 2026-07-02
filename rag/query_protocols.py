# ingest_protocols.py로 적재한 ChromaDB 컬렉션이 잘 들어갔는지 확인하는 간단한 검색 스크립트.
# 사용법: export UPSTAGE_API_KEY=... 후 python query_protocols.py

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from chroma_client import get_chroma_client

load_dotenv(Path(__file__).parent / ".env")
UPSTAGE_API_KEY = os.environ["UPSTAGE_API_KEY"]

embed_client = OpenAI(api_key=UPSTAGE_API_KEY, base_url="https://api.upstage.ai/v1/solar")
collection = get_chroma_client().get_collection("rehab_protocols")


def search(query: str, condition: str | None = None, n_results: int = 3):
    query_embedding = embed_client.embeddings.create(model="embedding-query", input=[query]).data[0].embedding
    where = {"condition": condition} if condition else None
    return collection.query(query_embeddings=[query_embedding], n_results=n_results, where=where)


if __name__ == "__main__":
    result = search("2주차 ACL 재건 금기 동작", condition="KNEE")
    for doc, meta in zip(result["documents"][0], result["metadatas"][0]):
        print(meta)
        print(doc[:200])
        print("---")
