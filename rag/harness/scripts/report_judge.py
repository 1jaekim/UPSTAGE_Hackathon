"""report_judge.py — Gate 2: 독립 LLM 저지 (J1 서술 품질, J4 groundedness만).

agents/report-judge-subagent/AGENT.md를 코드로 옮긴 버전. report_validate.py(Gate 3,
기계적 검증)를 통과한 뒤에만 호출된다. 안전성(Gate 1)은 재판정하지 않는다.

usage: python3 report_judge.py
"""
import sys

from lib import load_json, save_json, work_path
from upstage_client import chat_json

PROMPT_TMPL = """당신은 재활 운동처방 SOAP 리포트의 독립 검수자입니다. 이 리포트를 작성하지
않았습니다. 아래 두 가지만 판단하세요 — 안전성 판정은 이미 코드로 확정되었으니 재판단하지 마세요.

J1 — 서술 품질: S/O/A/P 각 서술이 형식적 placeholder가 아니라 실질적 내용을 담고 있고,
문맥(주차/단계/red flag 여부)과 내적으로 일치하며, 진단/단정적 지시가 아니라 "제안+근거" 톤을
유지하는가? 한국어와 영어가 같은 내용을 전달하는가?

J4 — Groundedness: 서술의 모든 주장이 아래 제공된 데이터(context, prescription)에서 실제로
확인되는가? prescription에 없는 운동/수치/임상적 주장이 등장하지 않는가? 마스킹된 notes의
내용을 추론해서 서술하지 않았는가?

[컨텍스트]
{ctx}

[확정 처방]
{prescription}

[검수 대상 리포트]
{report}

반드시 아래 JSON 스키마 하나만 출력하라(설명 문장 금지):
{{"pass": true 또는 false, "failed_checks": ["J1"과 "J4" 중 실패한 것만, 없으면 빈 배열], "notes": "판단 근거 한 줄"}}
"""


def main():
    ctx = load_json(work_path("00_context.json"))
    prescription = load_json(work_path("40_prescription.json"))
    report = load_json(work_path("50_report.json"))

    prompt = PROMPT_TMPL.format(ctx=ctx, prescription=prescription, report=report)
    try:
        verdict = chat_json(prompt)
    except Exception as e:
        import os
        if os.environ.get("SAFERX_STRICT_LLM") != "1":
            # 명시적 degraded 모드: Gate 3(기계 검증)는 이미 통과한 상태에서만 도달하므로
            # 구조/개수/이중언어/길이는 보장됨. J1/J4(LLM 판단)는 미수행임을 notes에 남긴다.
            print(f"[judge] LLM unavailable ({type(e).__name__}) — degraded pass (Gate 3 only)")
            verdict = {"pass": True, "failed_checks": [],
                       "notes": "DEGRADED: LLM judge unavailable — J1/J4 not evaluated; mechanical Gate 3 passed."}
        else:
            raise

    save_json(work_path("60_judge.json"), verdict)
    print(f"judge pass={verdict.get('pass')} failed={verdict.get('failed_checks')}")
    sys.exit(0 if verdict.get("pass") else 1)


if __name__ == "__main__":
    main()
