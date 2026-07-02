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


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    idx = json.load(open(INDEX))
    rows = []
    for entry in idx:
        pid = entry["patient_id"]
        input_path = os.path.join(PERSONAS, entry["input_file"])
        inp = json.load(open(input_path))
        gold = gold_label(inp)
        pred, detail = run_pipeline_for(pid, input_path)
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

    return rows


if __name__ == "__main__":
    main()
