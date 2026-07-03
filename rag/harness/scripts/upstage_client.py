"""Upstage Solar 채팅 호출 공용 헬퍼. reporter.py/report_judge.py/notes_screen.py에서만
쓴다(하네스의 LLM 지점 — 나머지 스크립트는 전부 결정론 코드). notes_screen.py는 안전
판정을 직접 하지 않고 "사람이 봐야 하는가"라는 이진 신호만 내므로 이 경계를 안 깬다."""
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


# Upstage OpenAI 호환 API의 현행 base는 /v1 이다 (solar-pro2 등 최신 모델).
# /v1/solar 는 구(legacy) 경로 — 환경에 따라 한쪽만 열려 있을 수 있어 둘 다 시도한다.
BASE_URLS = [
    os.environ.get("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1"),
    "https://api.upstage.ai/v1/solar",
]

MODEL = os.environ.get("UPSTAGE_CHAT_MODEL", "solar-pro2")

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json_object(text: str) -> str:
    """모델이 지시를 어기고 JSON 뒤에 설명 문장을 덧붙이는 경우가 있어(예: solar-pro2가
    "근거:" 같은 부연을 붙임), 첫 '{'부터 괄호 균형이 맞는 지점까지만 잘라낸다.
    순수 JSON이면 그대로 반환(문자열 슬라이싱 오버헤드만 추가될 뿐 동작은 동일)."""
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:]


def chat_json(prompt: str, temperature: float = 0.0) -> dict:
    """프롬프트를 보내고 JSON 객체 하나를 파싱해 반환. 코드펜스나 JSON 뒤에 붙는 부연
    설명이 있어도 첫 JSON 객체만 추출한다. base_url은 현행(/v1) → legacy(/v1/solar) 순."""
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
            text = _extract_json_object(text)
            return json.loads(text)
        except Exception as e:
            last_err = e
            print(f"[upstage] {base} 실패: {type(e).__name__}: {e}")
    raise last_err
