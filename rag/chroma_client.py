# rag/.env에 CHROMA_API_KEY가 있으면 Chroma Cloud로, 없으면 로컬 파일(rag/chroma_db)로 붙는다.
import os
from pathlib import Path

import chromadb

CHROMA_DIR = Path(__file__).parent / "chroma_db"


def get_chroma_client() -> chromadb.ClientAPI:
    api_key = os.environ.get("CHROMA_API_KEY")
    if api_key:
        return chromadb.CloudClient(
            api_key=api_key,
            tenant=os.environ["CHROMA_TENANT"],
            database=os.environ["CHROMA_DATABASE"],
        )
    return chromadb.PersistentClient(path=str(CHROMA_DIR))
