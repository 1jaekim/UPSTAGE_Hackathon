"""chroma_client.py — 연결 분기 (CHROMADB_TIMELY_GUIDE.md §1/§6 계약).

CHROMA_API_KEY가 있으면 Chroma Cloud, 없으면 로컬 파일(rag/chroma_db).
키는 rag/.env에서 읽는다 — 코드·문서에 원문 기재 금지.
"""
import os

TENANT = "68a6db9d-c8a8-4f7c-879f-b5d843ecc7c4"
DATABASE = "SpineSurgery2ThousandWon"
COLLECTION = "rehab_protocols"
_HERE = os.path.dirname(os.path.abspath(__file__))


def load_env(path=None):
    """단순 KEY=VALUE 파서. 이미 있는 os.environ 값은 덮지 않는다."""
    path = path or os.path.join(_HERE, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def get_collection():
    """Cloud 우선, 키 없으면 로컬. 반환: (collection, mode)"""
    import chromadb
    load_env()
    key = os.environ.get("CHROMA_API_KEY")
    if key:
        client = chromadb.CloudClient(api_key=key, tenant=TENANT, database=DATABASE)
        return client.get_collection(COLLECTION), "cloud"
    client = chromadb.PersistentClient(path=os.path.join(_HERE, "chroma_db"))
    return client.get_or_create_collection(COLLECTION), "local"
