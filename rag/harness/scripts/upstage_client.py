"""Upstage Solar 채팅 호출 공용 헬퍼. reporter.py/report_judge.py에서만 쓴다
(하네스의 유일한 두 LLM 지점 — 나머지 스크립트는 전부 결정론 코드)."""
import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

_ENV_LOADED = False


def _ensure_env():
    global _ENV_LOADED
    if not _ENV_LOADED:
        # rag/.env를 찾는다 (scripts/의 조상 디렉토리)
        here = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(here, "..", "..", ".env")
        load_dotenv(candidate)
        _ENV_LOADED = True


def _client():
    _ensure_env()
    return OpenAI(api_key=os.environ["UPSTAGE_API_KEY"], base_url="https://api.upstage.ai/v1/solar")


MODEL = os.environ.get("UPSTAGE_CHAT_MODEL", "solar-pro2")

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def chat_json(prompt: str, temperature: float = 0.0) -> dict:
    """프롬프트를 보내고 JSON 객체 하나를 파싱해 반환. 코드펜스가 붙어와도 벗겨낸다."""
    resp = _client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    text = resp.choices[0].message.content.strip()
    text = _FENCE_RE.sub("", text).strip()
    return json.loads(text)
