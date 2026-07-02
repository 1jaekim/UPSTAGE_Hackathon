"""report_validate.py — Gate 3(스키마) + 기계 검증 가능한 J체크 (코드, LLM 아님).

reporter-subagent가 쓴 work/50_report.json에 대해:
  V-PARSE  JSON 파싱 (spec §6-3 — 사실상 최우선 게이트)
  V-SCHEMA §5 필수 키·타입
  V-J2     exercises 정확히 5개 (특이사항으로 PT에게 위임된 경우엔 0개도 허용)
  V-J3     각 운동 rationale/source 존재 (세트/반복/빈도는 PT 재량이라 시스템이 안 다룸)
  V-J5     필수 서술 필드 ko+en 모두 비어있지 않음
  V-J6     길이 예산: 서술 텍스트 총합 ≤ 3500자 (A4 1장 프록시, DECISIONS.md #3)
  V-SAFE   safety.final_gate_passed == true, 전 운동 safety_checked == true

LLM 저지(Gate 2)는 이 검증 통과 후 J1(서술 품질)·J4(groundedness)만 본다.

usage: python3 report_validate.py
"""
import json, sys
from lib import work_path, save_json

LENGTH_BUDGET = 3500
EX_REQUIRED = ["rationale", "source"]


def bilingual_ok(node):
    return (isinstance(node, dict) and
            isinstance(node.get("ko"), str) and node["ko"].strip() != "" and
            isinstance(node.get("en"), str) and node["en"].strip() != "")


def collect_text(node, acc):
    if isinstance(node, dict):
        for v in node.values():
            collect_text(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_text(v, acc)
    elif isinstance(node, str):
        acc.append(node)


def main():
    fails = []
    try:
        with open(work_path("50_report.json"), encoding="utf-8") as f:
            rpt = json.load(f)
    except Exception as e:
        save_json(work_path("55_validation.json"),
                  {"pass": False, "fails": [{"check": "V-PARSE", "detail": str(e)}]})
        print("FAIL V-PARSE")
        sys.exit(30)

    # V-SCHEMA
    for key in ("report_meta", "soap", "manual_review", "safety"):
        if key not in rpt:
            fails.append({"check": "V-SCHEMA", "detail": f"missing top-level key: {key}"})
    soap = rpt.get("soap", {})
    for sec in ("subjective", "objective", "assessment", "plan"):
        if sec not in soap:
            fails.append({"check": "V-SCHEMA", "detail": f"missing soap.{sec}"})

    exercises = soap.get("plan", {}).get("exercises", [])

    # V-J2 (0개 = 특이사항으로 PT에게 위임된 정당한 케이스)
    if len(exercises) not in (0, 5):
        fails.append({"check": "V-J2", "detail": f"exercises count = {len(exercises)} (must be 0 or 5)"})

    # V-J3
    for ex in exercises:
        name = ex.get("name", {}).get("en", "?")
        for f in EX_REQUIRED:
            v = ex.get(f)
            if v is None or v == "" or v == {}:
                fails.append({"check": "V-J3", "detail": f"{name}: missing {f}"})

    # V-J5 (이중언어)
    for sec in ("subjective", "objective", "assessment"):
        if sec in soap and not bilingual_ok(soap[sec]):
            fails.append({"check": "V-J5", "detail": f"soap.{sec} not bilingual/non-empty"})
    plan = soap.get("plan", {})
    if plan and not (isinstance(plan.get("ko"), str) and plan["ko"].strip()
                     and isinstance(plan.get("en"), str) and plan["en"].strip()):
        fails.append({"check": "V-J5", "detail": "soap.plan summary not bilingual/non-empty"})
    for ex in exercises:
        for f in ("name", "rationale"):
            if not bilingual_ok(ex.get(f, {})):
                fails.append({"check": "V-J5",
                              "detail": f'{ex.get("name", {}).get("en", "?")}: {f} not bilingual'})

    # V-J6 (길이 예산)
    acc = []
    collect_text(soap, acc)
    total = sum(len(s) for s in acc)
    if total > LENGTH_BUDGET:
        fails.append({"check": "V-J6", "detail": f"narrative length {total} > {LENGTH_BUDGET}"})

    # V-SAFE
    if rpt.get("safety", {}).get("final_gate_passed") is not True:
        fails.append({"check": "V-SAFE", "detail": "safety.final_gate_passed != true"})
    if rpt.get("safety", {}).get("violations") != []:
        fails.append({"check": "V-SAFE", "detail": "safety.violations not empty"})
    for ex in exercises:
        if ex.get("safety_checked") is not True:
            fails.append({"check": "V-SAFE",
                          "detail": f'{ex.get("name", {}).get("en", "?")}: safety_checked != true'})

    ok = not fails
    save_json(work_path("55_validation.json"),
              {"pass": ok, "narrative_chars": total, "fails": fails})
    print("PASS" if ok else f"FAIL ({len(fails)} issues)")
    sys.exit(0 if ok else 31)


if __name__ == "__main__":
    main()
