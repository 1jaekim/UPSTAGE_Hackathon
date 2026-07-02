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
        # saferx-v2/rag/.env를 우선 시도하고, 없으면 조상의 rag/.env로 폴백.
        # 두 위치 모두 지원해서 폴더가 이동해도 키 위치를 다시 안 잡아도 된다.
        here = os.path.dirname(os.path.abspath(__file__))
        for candidate in [
            os.path.join(here, "..", "rag", ".env"),        # saferx-v2/rag/.env
            os.path.join(here, "..", "..", "rag", ".env"),  # <project>/rag/.env (legacy)
        ]:
            if os.path.exists(candidate):
                load_dotenv(candidate)
        _ENV_LOADED = True


# Upstage OpenAI 호환 API의 현행 base는 /v1 이다 (solar-pro2 등 최신 모델).
# /v1/solar 는 구(legacy) 경로 — 환경에 따라 한쪽만 열려 있을 수 있어 둘 다 시도한다.
BASE_URLS = [
    os.environ.get("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1"),
    "https://api.upstage.ai/v1/solar",
]

MODEL = os.environ.get("UPSTAGE_CHAT_MODEL", "solar-pro2")

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def chat_json(prompt: str, temperature: float = 0.0) -> dict:
    """프롬프트를 보내고 JSON 객체 하나를 파싱해 반환. 코드펜스가 붙어와도 벗겨낸다.
    base_url은 현행(/v1) → legacy(/v1/solar) 순으로 시도한다."""
    _ensure_env()
    last_err = None
    for base in dict.fromkeys(BASE_URLS):  # 중복 제거, 순서 유지
        try:
            client = OpenAI(api_key=os.environ["UPSTAGE_API_KEY"], base_url=base)
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            text = resp.choices[0].message.content.strip()
            text = _FENCE_RE.sub("", text).strip()
            return json.loads(text)
        except Exception as e:
            last_err = e
            print(f"[upstage] {base} 실패: {type(e).__name__}: {e}")
    raise last_err
