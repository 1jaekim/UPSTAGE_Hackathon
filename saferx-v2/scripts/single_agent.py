"""single_agent.py — 단일 LLM Baseline.

멀티에이전트 파이프라인(extract→retrieve→safety→correct→generate→reporter→
validate→judge) 전체를 하나의 Upstage Solar 호출로 대체한다.
프롬프트에는 게이트 규칙과 라이브러리 요약을 넣고, LLM이 스스로 status와
처방을 결정하게 한다 — 즉 스크립트가 아니라 LLM 지시 준수만이 정답 보장.

usage:
  python3 saferx-v2/scripts/single_agent.py <input.json>       # 개별 실행
  (평가 배치는 eval_f1.py --mode single 로 실행)

반환 JSON:
  {"status": "...", "exercises": [{"name_en": "...", "name_ko": "..."}, ...]}
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, load_json
from upstage_client import _ensure_env, BASE_URLS, MODEL

from openai import OpenAI


def _extract_first_json(text: str) -> dict:
    """JSON 뒤에 부연설명이 붙어도 첫 {…} 블록만 뽑아 파싱한다.
    Solar가 자꾸 뒤에 설명을 덧붙이는 경우 대응."""
    # 코드펜스 제거
    text = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", text.strip(), flags=re.MULTILINE)
    # 첫 { 부터 균형 잡힌 } 까지 슬라이싱
    depth, start = 0, -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                return json.loads(text[start:i + 1])
    raise ValueError(f"no balanced JSON object in response: {text[:200]}")


def _call_llm(prompt: str, temperature: float = 0.0) -> str:
    _ensure_env()
    last_err = None
    for base in dict.fromkeys(BASE_URLS):
        try:
            client = OpenAI(api_key=os.environ["UPSTAGE_API_KEY"], base_url=base)
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system",
                     "content": "You output exactly one JSON object and nothing else. "
                                "No prose, no code fences, no trailing text."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_err = e
    raise last_err


_LIBRARY_CACHE = None


def library_summary():
    global _LIBRARY_CACHE
    if _LIBRARY_CACHE is not None:
        return _LIBRARY_CACHE
    lib = load_json(os.path.join(DATA, "exercise_library.json"))
    rows = []
    for e in lib["exercises"]:
        rows.append(f'  - {e["name"]["en"]:35s} | phases={",".join(e["phases"])} | '
                    f'load={e["load_type"]:9s} | chain={e["kinetic_chain"]:5s} | '
                    f'muscle={e["target_muscle"]}')
    _LIBRARY_CACHE = "\n".join(rows)
    return _LIBRARY_CACHE


PROMPT = """당신은 무릎 재활 처방 시스템입니다. 아래 입력을 보고 단 하나의 JSON을 출력하세요.

## 게이트 규칙 (반드시 순서대로 검사)
1. surgery != "ACL_RECON" → status = "unsupported_surgery"
2. surgery_details.graft_type != "hamstring_autograft" → status = "unsupported_case"
3. concomitant_procedure != null → status = "manual_review_required"
4. pain_nrs != null and pain_nrs >= 6 → status = "red_flag"
5. 위 어느 조건에도 걸리지 않으면 → status = "ready_for_reporter"

## 처방 선택 규칙 (status == "ready_for_reporter"일 때만)
- 아래 exercise library에서 정확히 3개를 선택
- 선택 기준: 환자의 phase에 적합한 phases에 포함된 운동, priority가 낮을수록 우선
- surgery_details.phase와 week_post_op(주차)를 모두 고려하여 낮은 쪽 phase 채택
- red flag(NRS>=7 또는 swelling=true) 있으면 dynamic load_type 제외 (isometric만)
- PHASE I–II이면 open kinetic_chain 저항 신전 금지
- 12주 미만이면 저항성 hamstring 굴곡 금지
- status != "ready_for_reporter"이면 exercises는 빈 배열 []

## Exercise Library
{library}

## 입력
{patient}

## 출력 (다른 텍스트 절대 금지, 코드펜스 금지)
{{"status": "ready_for_reporter" 또는 "unsupported_surgery" 또는 "unsupported_case" 또는 "manual_review_required" 또는 "red_flag" 또는 "insufficient_evidence" 또는 "failed",
 "exercises": [{{"name_en": "...", "name_ko": "..."}}, ...]}}
"""


def run_single(inp: dict) -> dict:
    prompt = PROMPT.format(library=library_summary(),
                           patient=json.dumps(inp, ensure_ascii=False, indent=2))
    try:
        raw = _call_llm(prompt)
        return _extract_first_json(raw)
    except Exception as e:
        return {"status": "error", "exercises": [], "error": f"{type(e).__name__}: {e}"}


def main():
    if len(sys.argv) != 2:
        print("usage: single_agent.py <input.json>", file=sys.stderr)
        sys.exit(2)
    inp = load_json(sys.argv[1])
    out = run_single(inp)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
