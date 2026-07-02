"""safety_judge.py — Gate 1: 결정론적 안전/완결성 판정 (코드, LLM 아님). spec §6-1.

두 모드:
  --mode safety        : work/10_candidates.json의 후보를 rule_table 대조
  --mode completeness  : work/40_prescription.json의 최종 3개를
                         (a) 안전 룰 재평가 — 용량·clamp 반영 최종 상태 기준 (dosage gap 봉합)
                         (b) COMP/DOS builtin 검사 (필드 누락·용량 변조)

판정 정책 (spec §6-1, 단위 정의는 DECISIONS.md #1):
  hard_violations = FIRE된 (운동 × hard 룰) 쌍의 개수 (soft·input_gate 제외)
  0        → approved
  1 – 10   → rejected_loop  (violations + correction_hint 반환 → corrector)
  ≥ 11     → red_flag       (run_pipeline이 status=red_flag로 기록)
  iteration > MAX_ITERATIONS(5) → failed 강등

usage: python3 safety_judge.py --mode safety|completeness
"""
import argparse, os, sys
from lib import load_json, save_json, work_path, match, DATA

MAX_ITERATIONS = 5
THRESH_FAIL = 11  # 전체 22룰의 절반 (spec §6-1 고정값)


def eval_safety_rules(rules, ctx, exercises):
    violations, manual_review = [], []
    checked = []
    for ex in exercises:
        ex_hard_fired = False
        for rule in rules:
            if rule["mode"] != "safety":
                continue
            if match(rule["patient_if"], ctx) and match(rule["exercise_if"], ex):
                entry = {"rule_id": rule["rule_id"], "title": rule["title"],
                         "exercise": ex["name"]["en"], "quote_ref": rule.get("quote_ref")}
                if rule["severity"] == "hard":
                    entry["correction_hint"] = rule.get("correction_hint", {})
                    violations.append(entry)
                    ex_hard_fired = True
                else:  # soft → 카운트 제외, manual_review만 (spec §6-1)
                    manual_review.append(entry)
        checked.append({"name_en": ex["name"]["en"], "safety_checked": not ex_hard_fired})
    return violations, manual_review, checked


def eval_completeness(rules, prescription, library):
    """COMP-01/02 + DOS-02 builtin."""
    fails = []
    lib_by_en = {e["name"]["en"]: e for e in library["exercises"]}
    for rule in rules:
        if rule["mode"] != "completeness":
            continue
        if rule.get("builtin") == "required_fields":
            for ex in prescription["exercises"]:
                for f in rule["required"]:
                    v = ex.get(f)
                    if v is None or v == "" or v == {}:
                        fails.append({"rule_id": rule["rule_id"], "exercise": ex["name"]["en"],
                                      "missing": f})
        elif rule.get("builtin") == "dosage_matches_library":
            for ex in prescription["exercises"]:
                src = lib_by_en.get(ex["name"]["en"])
                if src is None:
                    fails.append({"rule_id": rule["rule_id"], "exercise": ex["name"]["en"],
                                  "missing": "library_entry (invented exercise?)"})
                    continue
                for f in ("sets", "reps"):
                    if ex.get(f) is not None and ex[f] > src["dosage"][f]:
                        fails.append({"rule_id": rule["rule_id"], "exercise": ex["name"]["en"],
                                      "missing": f"{f} exceeds library ({ex[f]}>{src['dosage'][f]})"})
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["safety", "completeness"], required=True)
    args = ap.parse_args()

    ctx = load_json(work_path("00_context.json"))
    table = load_json(os.path.join(DATA, "rule_table.json"))
    rules = table["rules"]

    # input gate 재확인 (방어적 — extract 단계에서 이미 걸렀어야 함)
    for rule in rules:
        if rule["mode"] == "input_gate" and match(rule["patient_if"], ctx):
            out = {"decision": rule["outcome"], "gate_rule": rule["rule_id"],
                   "hard_violations": 0, "violations": [], "manual_review": []}
            save_json(work_path("20_safety.json"), out)
            print(f"decision={rule['outcome']} (input gate {rule['rule_id']})")
            sys.exit(13)

    if args.mode == "safety":
        cands = load_json(work_path("10_candidates.json"))
        iteration = cands.get("iteration", 1)
        violations, manual_review, checked = eval_safety_rules(rules, ctx, cands["candidates"])
        n = len(violations)
        if iteration > MAX_ITERATIONS:
            decision = "failed"
        elif n == 0:
            decision = "approved"
        elif n < THRESH_FAIL:
            decision = "rejected_loop"
        else:
            decision = "failed"
        out = {"mode": "safety", "decision": decision, "hard_violations": n,
               "violations": violations, "manual_review": manual_review,
               "iteration": iteration, "exercises_checked": checked}
        save_json(work_path("20_safety.json"), out)
        print(f"decision={decision} hard_violations={n} iter={iteration}")
        sys.exit({"approved": 0, "rejected_loop": 20, "failed": 21}[decision])

    # completeness 모드: 최종 3개에 대해 안전 룰 재평가 + builtin
    rx = load_json(work_path("40_prescription.json"))
    library = load_json(os.path.join(DATA, "exercise_library.json"))
    violations, manual_review, checked = eval_safety_rules(rules, ctx, rx["exercises"])
    comp_fails = eval_completeness(rules, rx, library)
    ok = not violations and not comp_fails
    out = {"mode": "completeness", "decision": "approved" if ok else "failed_completeness",
           "safety_recheck_violations": violations, "completeness_fails": comp_fails,
           "manual_review": manual_review, "exercises_checked": checked}
    save_json(work_path("45_completeness.json"), out)
    print(f"completeness decision={'approved' if ok else 'failed_completeness'}")
    sys.exit(0 if ok else 22)


if __name__ == "__main__":
    main()
