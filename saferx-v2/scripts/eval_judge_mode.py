"""eval_judge_mode.py — split vs combined 판정 아키텍처 성능 비교.

split(현행)    : reporter LLM → 코드 Gate3 → report-judge LLM (2 콜, 작성/심사 분리)
combined(실험) : reporter+self-judge를 한 LLM 콜에 결합 (1 콜, 자기 채점)

동일한 페르소나 30명에 대해 두 모드를 각각 돌리고 비교:
  - 최종 status F1 (이전 eval_f1과 동일 라벨 기준)
  - Gate 2 pass rate on first attempt (재시도 없이 통과한 비율)
  - LLM 호출 수 (비용/지연 프록시)
  - self-serving bias: combined가 자신을 실제로 fail시킨 횟수
  - cross-check: combined의 SOAP를 split의 report_judge로 재심사했을 때 pass율

usage: python3 saferx-v2/scripts/eval_judge_mode.py
"""
import json, os, subprocess, sys, tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS = os.path.join(ROOT, "samples", "personas")
INDEX = os.path.join(PERSONAS, "_index.json")

sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "rag"))
from harness_runner import run_harness_pipeline  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "scripts"))


def gold_label(inp: dict) -> str:
    if inp.get("surgery") != "ACL_RECON":
        return "unsupported_surgery"
    if inp["surgery_details"].get("graft_type") != "hamstring_autograft":
        return "unsupported_case"
    if inp.get("concomitant_procedure") is not None:
        return "manual_review_required"
    pain = inp.get("pain_nrs")
    if pain is not None and pain >= 6:
        return "red_flag"
    return "ready_for_reporter"


def run_all(mode: str, keep_report: bool = False) -> list[dict]:
    idx = json.load(open(INDEX))
    rows = []
    for entry in idx:
        pid = entry["patient_id"]
        input_path = os.path.join(PERSONAS, entry["input_file"])
        inp = json.load(open(input_path))
        gold = gold_label(inp)
        out = run_harness_pipeline(inp, judge_mode=mode)
        row = {
            "pid": pid, "gold": gold, "pred": out["status"],
            "detail": out.get("detail", ""),
            "llm_calls": out.get("llm_calls", 0),
            "iterations": out.get("iterations", 0),
        }
        if keep_report:
            row["report"] = out.get("report")
        rows.append(row)
    return rows


def cross_check_split_judge(combined_report: dict, context: dict, prescription: dict) -> dict:
    """combined이 만든 리포트를 split의 report_judge 프롬프트로 재심사.
    같은 텍스트에 대해 '작성자=심사자'와 '독립 심사자'의 판정이 다르면 self-serving bias."""
    from upstage_client import chat_json
    prompt = (
        "당신은 이 리포트를 작성하지 않은 독립 심사자입니다. J1(서술 품질)·J4(근거성)만 판정.\n\n"
        f"[컨텍스트]\n{json.dumps(context, ensure_ascii=False)}\n\n"
        f"[확정 처방]\n{json.dumps(prescription, ensure_ascii=False)}\n\n"
        f"[검수 대상 리포트]\n{json.dumps(combined_report, ensure_ascii=False)}\n\n"
        "다음 JSON 하나만 출력(다른 텍스트 금지):\n"
        '{"pass": true 또는 false, "failed_checks": ["J1"과 "J4" 중 실패한 것], "notes": "..."}'
    )
    try:
        return chat_json(prompt)
    except Exception as e:
        return {"pass": None, "error": f"{type(e).__name__}: {e}"}


def status_metrics(rows: list[dict]) -> dict:
    labels = sorted({r["gold"] for r in rows} | {r["pred"] for r in rows})
    cm = defaultdict(lambda: defaultdict(int))
    for r in rows:
        cm[r["gold"]][r["pred"]] += 1
    macro_f, weighted_f, total_support = 0.0, 0.0, 0
    per_class = {}
    for cls in labels:
        tp = cm[cls][cls]
        fp = sum(cm[g][cls] for g in labels if g != cls)
        fn = sum(cm[cls][p] for p in labels if p != cls)
        support = tp + fn
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        per_class[cls] = {"support": support, "tp": tp, "fp": fp, "fn": fn,
                          "p": p, "r": r, "f1": f}
        if support:
            macro_f += f
            weighted_f += f * support
            total_support += support
    n_gold = sum(1 for cls in labels if per_class[cls]["support"] > 0)
    macro_f /= n_gold if n_gold else 1
    weighted_f /= total_support if total_support else 1
    acc = sum(1 for r in rows if r["gold"] == r["pred"]) / len(rows)
    return {"accuracy": acc, "macro_f1": macro_f, "weighted_f1": weighted_f,
            "per_class": per_class}


def summarize(mode: str, rows: list[dict]) -> dict:
    m = status_metrics(rows)
    approved = [r for r in rows if r["pred"] == "ready_for_reporter"]
    per_row_calls = [r["llm_calls"] for r in rows if r["llm_calls"] > 0]
    # first-attempt success proxy: llm_calls == (2 for split, 1 for combined) means 1 attempt
    expected_first = 2 if mode == "split" else 1
    first_pass = sum(1 for r in approved if r["llm_calls"] == expected_first)
    max_calls = max(per_row_calls) if per_row_calls else 0
    return {
        "mode": mode, "n": len(rows),
        "accuracy": m["accuracy"], "macro_f1": m["macro_f1"], "weighted_f1": m["weighted_f1"],
        "approved": len(approved),
        "avg_llm_calls_over_approved": (
            sum(r["llm_calls"] for r in approved) / len(approved) if approved else 0.0
        ),
        "max_llm_calls": max_calls,
        "first_attempt_pass_rate": first_pass / len(approved) if approved else 0.0,
        "per_class": m["per_class"],
    }


def print_table(label: str, s: dict):
    print(f"\n=== {label} ===")
    print(f"  Accuracy         : {s['accuracy']:.3f}")
    print(f"  Macro F1         : {s['macro_f1']:.3f}")
    print(f"  Weighted F1      : {s['weighted_f1']:.3f}")
    print(f"  ready 처방       : {s['approved']}/{s['n']}")
    print(f"  평균 LLM 호출/성공: {s['avg_llm_calls_over_approved']:.2f}")
    print(f"  최대 LLM 호출    : {s['max_llm_calls']}")
    print(f"  1회 시도 통과율   : {s['first_attempt_pass_rate']*100:.1f}%")


def main():
    print("[eval_judge_mode] running SPLIT (multi-agent) …")
    split_rows = run_all("split")
    s_split = summarize("split", split_rows)

    print("[eval_judge_mode] running COMBINED …")
    combined_rows = run_all("combined", keep_report=True)
    s_combined = summarize("combined", combined_rows)

    print_table("SPLIT — 현행 (reporter + report-judge 분리)", s_split)
    print_table("COMBINED — 실험 (한 LLM이 작성+자기채점)", s_combined)

    print("\n=== 페르소나별 비교 (승인 케이스만) ===")
    print("pid   split_pred                 combined_pred             split_calls comb_calls")
    for a, b in zip(split_rows, combined_rows):
        if a["gold"] != "ready_for_reporter":
            continue
        print(f"  {a['pid']}  {a['pred']:26s} {b['pred']:26s}  "
              f"{a['llm_calls']:>4d}      {b['llm_calls']:>4d}")

    print("\n=== Cross-check: combined의 리포트를 독립 심사자에게 재심사 ===")
    print("(작성한 LLM = 자기 심사 vs 다른 LLM 인스턴스 = 독립 심사) 판정 일치 여부")
    print("pid   self_pass  cross_pass  agreement  notes")
    from harness_runner import run_harness_pipeline as _run  # noqa
    # combined 성공 케이스만 대상으로 독립 심사 요청
    from lib import load_json  # noqa: F401
    disagreements = 0
    checked = 0
    for r in combined_rows:
        if r["pred"] != "ready_for_reporter" or not r.get("report"):
            continue
        rep = r["report"]
        # 컨텍스트 재구성: 페르소나 파일에서 최소 컨텍스트 로드
        inp = json.load(open(os.path.join(PERSONAS, f"{r['pid']}.json")))
        ctx = {"surgery": inp["surgery"], "week_post_op": inp["week_post_op"],
               "phase": rep["report_meta"]["phase"],
               "pain_nrs": inp["pain_nrs"], "swelling": inp["swelling"],
               "graft_type": inp["surgery_details"]["graft_type"]}
        pres = {"exercises": rep["soap"]["plan"]["exercises"]}
        cross = cross_check_split_judge(rep, ctx, pres)
        agree = "?" if cross.get("pass") is None else (
            "✓" if cross["pass"] else "✗ (독립 판정: fail)")
        if cross.get("pass") is False:
            disagreements += 1
        checked += 1
        note = cross.get("notes", cross.get("error", ""))[:60]
        print(f"  {r['pid']}  self=pass  cross={cross.get('pass')}  {agree}  {note}")

    print()
    print(f"  독립 심사가 combined를 fail로 판정한 비율: "
          f"{disagreements}/{checked} = {disagreements*100/max(checked,1):.1f}%")
    if disagreements == 0:
        print("  → 이 데이터셋에서는 self-serving bias가 관측되지 않음.")
        print("  → 다만 이는 '위험이 없다'가 아니라 '이 8개 정상 케이스는 두 심사자가 동의'라는 뜻.")
        print("    실 위험 시연: 리포트에 의도적 오류를 주입(injection test)해야 편향이 드러남.")
    else:
        print(f"  → {disagreements}건에서 self-judge는 통과, 독립 심사는 실패 → self-serving bias 관측.")


if __name__ == "__main__":
    main()
