# 아킬레스건/고관절/어깨/무릎 물리치료 프로토콜 문서를 파싱해 ChromaDB에 적재하는 스크립트.
#
# 사용법:
#   1) rag/protocols/ 안에 파일을 넣는다. 파일명(확장자 제외)이 CONDITION_MAP의 key와
#      일치해야 한다 (achilles.pdf, hip.pdf, shoulder.pdf, knee.pdf 등). 다르면 CONDITION_MAP 수정.
#   2) pip install -r requirements.txt
#   3) export UPSTAGE_API_KEY=...
#   4) python ingest_protocols.py
#
# 주의: Document Parse API의 엔드포인트/응답 스키마는 Upstage 콘솔 최신 문서 기준으로
# 한 번 확인하세요 (버전에 따라 응답 필드명이 바뀔 수 있습니다).

import os
import re
from pathlib import Path

import chromadb
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")
UPSTAGE_API_KEY = os.environ["UPSTAGE_API_KEY"]
PROTOCOLS_DIR = Path(__file__).parent / "protocols"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "rehab_protocols"

# 파일명(확장자 제외, 소문자) -> (condition 코드, 한글 라벨)
CONDITION_MAP = {
    "achilles": ("ACHILLES", "아킬레스건"),
    "hip": ("HIP", "고관절"),
    "shoulder": ("SHOULDER", "어깨"),
    "knee": ("KNEE", "무릎"),
}

# 한글 "0~2주"/"주 0-3"과 영문 "0-3 weeks"/"Weeks 1-4" 순서를 모두 잡기 위한 패턴
STAGE_WEEK_RE = re.compile(
    r"week[s]?\s*(?P<a1>\d+)\s*[-–~]\s*(?P<a2>\d+)"
    r"|(?P<b1>\d+)\s*[-–~]\s*(?P<b2>\d+)\s*(?:주|weeks?)",
    re.IGNORECASE,
)

# 문서마다 heading 태그(h1~h6) 사용이 일관되지 않아(같은 문서 안에서도 단계 제목이
# <p>로 나오기도 함), 태그 종류 대신 텍스트에 "단계 표시" 패턴이 있는지로 섹션을 나눈다.
PHASE_MARKER_RE = re.compile(
    r"phase\s+[ivx]+|week[s]?\s*\d|day\s*\d+\s*(?:to|-)\s*\d+|\d+\s*[-–~]\s*\d+\s*주|급성기|아급성기|기능\s*회복기|보호기",
    re.IGNORECASE,
)

embed_client = OpenAI(api_key=UPSTAGE_API_KEY, base_url="https://api.upstage.ai/v1/solar")


def parse_document(file_path: Path) -> str:
    """Upstage Document Parse API로 문서를 HTML로 변환.

    content.markdown/content.text는 문서에 따라 빈 문자열로 오는 경우가 있어
    항상 채워지는 content.html을 사용한다 (표까지 구조가 보존됨).
    """
    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://api.upstage.ai/v1/document-digitization",
            headers={"Authorization": f"Bearer {UPSTAGE_API_KEY}"},
            files={"document": f},
            data={"model": "document-parse"},
        )
    resp.raise_for_status()
    return resp.json()["content"]["html"]


def _element_to_text(tag) -> str:
    for br in tag.find_all("br"):
        br.replace_with("\n")
    if tag.name == "table":
        rows = []
        for tr in tag.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
            cells = [c for c in cells if c]
            if cells:
                rows.append(" | ".join(cells))
        return "\n".join(rows)
    return tag.get_text(strip=True)


def split_into_sections(html: str) -> list[tuple[str, str]]:
    """단계(phase/week) 표시가 있는 블록을 새 섹션의 heading으로 삼아 분할.
    표는 행 단위 텍스트로 변환. 마커를 하나도 못 찾으면 일정 개수 단위로 강제 분할."""
    soup = BeautifulSoup(html, "html.parser")
    blocks = [
        text
        for tag in soup.find_all(recursive=False)
        if tag.name != "br" and (text := _element_to_text(tag).strip())
    ]
    if not blocks:
        return []

    sections: list[tuple[str, str]] = []
    heading = blocks[0]
    body: list[str] = []
    for block in blocks[1:]:
        if len(block) < 120 and PHASE_MARKER_RE.search(block):
            if body:
                sections.append((heading, "\n".join(body).strip()))
            heading = block
            body = []
        else:
            body.append(block)
    if body:
        sections.append((heading, "\n".join(body).strip()))
    sections = [(h, b) for h, b in sections if b]

    if len(sections) <= 1:
        # 단계 마커를 못 찾은 문서: 블록 6개씩 묶어서 강제 분할
        sections = []
        chunk_size = 6
        for i in range(0, len(blocks), chunk_size):
            chunk = blocks[i : i + chunk_size]
            sections.append((chunk[0][:60], "\n".join(chunk)))

    return sections


def extract_week_range(text: str) -> tuple[int, int]:
    match = STAGE_WEEK_RE.search(text)
    if not match:
        return -1, -1
    if match.group("a1"):
        return int(match.group("a1")), int(match.group("a2"))
    return int(match.group("b1")), int(match.group("b2"))


def embed_passages(texts: list[str]) -> list[list[float]]:
    resp = embed_client.embeddings.create(model="embedding-passage", input=texts)
    return [d.embedding for d in resp.data]


def main() -> None:
    chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = chroma.get_or_create_collection(COLLECTION_NAME)

    for file_path in sorted(PROTOCOLS_DIR.glob("*")):
        stem = file_path.stem.lower()
        if stem not in CONDITION_MAP:
            print(f"[skip] {file_path.name}: CONDITION_MAP에 매핑 없음")
            continue
        condition_code, condition_label = CONDITION_MAP[stem]

        print(f"[parse] {file_path.name} ({condition_label})")
        html = parse_document(file_path)
        sections = split_into_sections(html)
        if not sections:
            print(f"  -> 경고: 섹션을 하나도 못 찾음, 건너뜀")
            continue

        ids, docs, metadatas = [], [], []
        for i, (heading, body) in enumerate(sections):
            week_min, week_max = extract_week_range(f"{heading} {body[:200]}")
            ids.append(f"{condition_code}-{i}")
            docs.append(f"{heading}\n{body}")
            metadatas.append(
                {
                    "condition": condition_code,
                    "condition_label": condition_label,
                    "section_title": heading,
                    "week_min": week_min,
                    "week_max": week_max,
                    "source_file": file_path.name,
                }
            )

        embeddings = embed_passages(docs)
        collection.upsert(ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings)
        print(f"  -> {len(ids)}개 섹션 적재 완료")

    print("전체 적재 완료. 컬렉션 카운트:", collection.count())


if __name__ == "__main__":
    main()
