"""eval_f1.py — 페르소나 30명에 대한 파이프라인 상태 분류 성능 평가.

정답셋(gold):
  samples/personas/_index.json의 expected_status를 기본으로 하되,
  현행 규칙(NRS≥6→red_flag, concomitant→manual_review, ACL_RECON 아님→
  unsupported_surgery)에 맞춰 결정론적으로 재계산한다. _index.json 라벨을
  그대로 쓰지 않는 이유는 라벨이 이전 규칙(NRS≥7)으로 작성됐고, 현행 코드
  기준의 F1이 필요하기 때문.

예측(pred):
  각 페르소나 JSON을 run_pipeline.py에 넣어 얻은 status.

출력:
  per-persona pred vs gold, 혼동 행렬, 클래스별 precision/recall/F1,
  macro-F1 / weighted-F1 / accuracy.

usage: python3 saferx-v2/scripts/eval_f1.py [--verbose]
"""
import json, os, subprocess, sys, tempfile, argparse
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS = os.path.join(ROOT, "samples", "personas")
INDEX = os.path.join(PERSONAS, "_index.json")
RUN_PIPE = os.path.join(ROOT, "scripts", "run_pipeline.py")


def gold_label(inp: dict) -> str:
    """현행 파이프라인 규칙을 정답 함수로 그대로 옮긴 것.
    extract_redact.py의 게이트 순서(unsupported → concomitant → NRS≥6)와
    일치. 나머지(insufficient_evidence, red_flag by hard≥11, failed 등)는
    데이터에 의존해서 결정되므로 gold=ready_for_reporter로 두고 실측이
    더 나쁘게 나올 때 오분류로 잡힌다."""
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


def run_pipeline_for(pid: str, input_path: str) -> tuple[str, str]:
    work = tempfile.mkdtemp(prefix=f"saferx_eval_{pid}_")
    env = {**os.environ, "SAFERX_WORK_DIR": work}
    r = subprocess.run([sys.executable, RUN_PIPE, input_path],
                       capture_output=True, text=True, env=env)
    status_path = os.path.join(work, "99_status.json")
    if not os.path.exists(status_path):
        return "error", f"no status file; stderr={r.stderr[-200:]}"
    doc = json.load(open(status_path))
    return doc["status"], doc.get("detail", "")


_SINGLE_AUDIT: list[dict] = []


def _audit_single_picks(inp: dict, picks: list[dict]) -> dict:
    """Single agent가 고른 운동을 rule_table로 재검증. 라이브러리에서 이름 매칭 실패
    → 존재하지 않는 운동을 지어낸 hallucination. 매칭 성공 → safety_judge 로직으로
    hard 위반 개수 계산."""
    from lib import load_json, DATA, match, effective_phase
    lib = load_json(os.path.join(DATA, "exercise_library.json"))
    by_en = {e["name"]["en"].lower(): e for e in lib["exercises"]}
    rules = load_json(os.path.join(DATA, "rule_table.json"))["rules"]

    week = inp["week_post_op"]
    declared = inp["surgery_details"]["phase"]
    eff, _, _ = effective_phase(week, declared)
    ctx = {
        "surgery": inp["surgery"], "week_post_op": week,
        "phase": eff, "phase_declared": declared,
        "graft_type": inp["surgery_details"]["graft_type"],
        "pain_nrs": inp.get("pain_nrs"), "swelling": inp["swelling"],
        "flags": {"red_flag": (inp.get("pain_nrs") or 0) >= 7 or inp["swelling"]},
    }
    hallucinated, unsafe_pairs = [], []
    for p in picks:
        name_en = (p.get("name_en") or "").lower().strip()
        src = by_en.get(name_en)
        if src is None:
            hallucinated.append(p.get("name_en", "?"))
            continue
        # phase 적합성 (라이브러리의 phases 목록에 없으면 부적합)
        if eff not in src.get("phases", []):
            unsafe_pairs.append((src["name"]["en"], f"phase_mismatch({eff} not in {src['phases']})"))
        for rule in rules:
            if rule["mode"] != "safety" or rule["severity"] != "hard":
                continue
            if match(rule["patient_if"], ctx) and match(rule["exercise_if"], src):
                unsafe_pairs.append((src["name"]["en"], rule["rule_id"]))
    return {"hallucinated": hallucinated, "unsafe": unsafe_pairs,
            "n_picks": len(picks), "n_hallucinated": len(hallucinated),
            "n_unsafe": len(unsafe_pairs)}


def run_single_agent_for(pid: str, input_path: str) -> tuple[str, str]:
    # 단일 LLM baseline: prompt에 규칙+라이브러리를 넣고 status를 스스로 판단
    from single_agent import run_single
    inp = json.load(open(input_path))
    out = run_single(inp)
    status = out.get("status", "error")
    picks = out.get("exercises", [])
    audit = _audit_single_picks(inp, picks) if status == "ready_for_reporter" else None
    _SINGLE_AUDIT.append({"pid": pid, "status": status, "audit": audit})
    tag = f"n_ex={len(picks)}"
    if audit:
        tag += f" hallu={audit['n_hallucinated']} unsafe={audit['n_unsafe']}"
    return status, tag


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--mode", choices=["multi", "single"], default="multi",
                    help="multi = 멀티에이전트 파이프라인 / single = 단일 LLM baseline")
    args = ap.parse_args()

    runner = run_pipeline_for if args.mode == "multi" else run_single_agent_for
    print(f"=== MODE: {args.mode.upper()} ===")

    idx = json.load(open(INDEX))
    rows = []
    for entry in idx:
        pid = entry["patient_id"]
        input_path = os.path.join(PERSONAS, entry["input_file"])
        inp = json.load(open(input_path))
        gold = gold_label(inp)
        pred, detail = runner(pid, input_path)
        rows.append({"pid": pid, "gold": gold, "pred": pred, "detail": detail,
                     "test_intent": entry.get("test_intent")})
        mark = "✓" if pred == gold else "✗"
        if args.verbose or pred != gold:
            print(f"  {mark} {pid} [{entry.get('test_intent','?'):>14}]  "
                  f"gold={gold:<25} pred={pred:<25} {detail}")

    print()
    print("=" * 70)
    print("Confusion matrix (gold ↓ / pred →)")
    labels = sorted({r["gold"] for r in rows} | {r["pred"] for r in rows})
    cm = defaultdict(lambda: defaultdict(int))
    for r in rows:
        cm[r["gold"]][r["pred"]] += 1
    header = "gold\\pred".ljust(24) + "".join(l[:12].rjust(13) for l in labels) + "  total"
    print(header)
    for g in labels:
        row = g.ljust(24)
        total = 0
        for p in labels:
            n = cm[g][p]; total += n
            row += (str(n) if n else "·").rjust(13)
        row += str(total).rjust(7)
        print(row)

    print()
    print("=" * 70)
    print("Per-class metrics")
    print("class".ljust(28) + "support   TP   FP   FN     P      R      F1")
    macro_f = 0.0
    weighted_f = 0.0
    total_support = 0
    for cls in labels:
        tp = cm[cls][cls]
        fp = sum(cm[g][cls] for g in labels if g != cls)
        fn = sum(cm[cls][p] for p in labels if p != cls)
        support = tp + fn
        p, r, f = prf(tp, fp, fn)
        if support:  # 정답에 존재하는 클래스만 macro 평균 대상
            macro_f += f
            weighted_f += f * support
            total_support += support
        print(f"  {cls.ljust(26)}{str(support).rjust(7)}"
              f"{str(tp).rjust(5)}{str(fp).rjust(5)}{str(fn).rjust(5)}"
              f"  {p:5.3f}  {r:5.3f}  {f:5.3f}")

    n_gold_classes = sum(1 for cls in labels if cm[cls][cls] + sum(cm[cls][p] for p in labels if p != cls))
    macro_f = macro_f / n_gold_classes if n_gold_classes else 0.0
    weighted_f = weighted_f / total_support if total_support else 0.0
    acc = sum(1 for r in rows if r["gold"] == r["pred"]) / len(rows)

    print()
    print("=" * 70)
    print(f"Accuracy       : {acc:.3f} ({sum(1 for r in rows if r['gold']==r['pred'])}/{len(rows)})")
    print(f"Macro   F1     : {macro_f:.3f}")
    print(f"Weighted F1    : {weighted_f:.3f}")

    # 단일 에이전트일 때는 실제 선택된 운동의 안전 감사도 리포트한다.
    if args.mode == "single" and _SINGLE_AUDIT:
        approved = [x for x in _SINGLE_AUDIT if x["status"] == "ready_for_reporter"]
        total_picks = sum(x["audit"]["n_picks"] for x in approved)
        total_hallu = sum(x["audit"]["n_hallucinated"] for x in approved)
        total_unsafe = sum(x["audit"]["n_unsafe"] for x in approved)
        clean = sum(1 for x in approved if x["audit"]["n_hallucinated"] == 0 and x["audit"]["n_unsafe"] == 0)
        print()
        print("=" * 70)
        print("Single-agent 처방 안전 감사 (rule_table + library 재검증)")
        print(f"  ready_for_reporter 케이스   : {len(approved)}")
        print(f"  총 뽑은 운동 수              : {total_picks}")
        print(f"  라이브러리에 없는 운동(할루) : {total_hallu}")
        print(f"  hard 안전 규칙 위반 쌍       : {total_unsafe}")
        print(f"  전부 통과한 처방              : {clean}/{len(approved)}")
        print()
        print("  세부 (문제 있는 케이스만):")
        for x in approved:
            a = x["audit"]
            if a["n_hallucinated"] or a["n_unsafe"]:
                print(f"    {x['pid']}: hallu={a['hallucinated']} unsafe={a['unsafe']}")

    return rows


if __name__ == "__main__":
    main()
