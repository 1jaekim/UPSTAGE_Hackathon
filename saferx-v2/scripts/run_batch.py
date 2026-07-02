"""run_batch.py — 페르소나 전체 배치 실행 + 기대 상태 대조 (코드).

각 페르소나에 대해 run_pipeline.py를 돌리고:
  status(99) · red_flag/mismatch 플래그(00) · 처방 5개 이름(40) · 판정(20)
을 수집해 work/batch_report.json + 콘솔 표로 요약한다.
_index.json의 expected_status와 실제 status를 대조해 PASS/FAIL을 매긴다.

usage: python3 run_batch.py <personas_dir>
"""
import glob, json, os, subprocess, sys
from lib import ROOT, WORK, save_json

PY = sys.executable


def read(name):
    p = os.path.join(WORK, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def run_one(inp_path):
    for f in glob.glob(os.path.join(WORK, "*.json")):
        os.remove(f)
    r = subprocess.run([PY, os.path.join(ROOT, "scripts", "run_pipeline.py"), inp_path],
                       capture_output=True, text=True)
    status = (read("99_status.json") or {}).get("status", f"error rc={r.returncode}")
    ctx, safety, rx = read("00_context.json"), read("20_safety.json"), read("40_prescription.json")
    row = {"status": status,
           "red_flag": bool(ctx and ctx["flags"]["red_flag"]),
           "phase_week_mismatch": bool(ctx and ctx["flags"]["phase_week_mismatch"]),
           "effective_phase": ctx and ctx.get("phase"),
           "iterations": safety and safety.get("iteration"),
           "exercises": [e["name"]["ko"] for e in rx["exercises"]] if rx and rx.get("exercises") else []}
    return row


def main(pdir):
    index = json.load(open(os.path.join(pdir, "_index.json"), encoding="utf-8"))
    results, n_pass = [], 0
    for meta in index:
        row = run_one(os.path.join(pdir, meta["input_file"]))
        ok = row["status"] == meta["expected_status"]
        n_pass += ok
        results.append({**meta, **row, "match": ok})
        mark = "PASS" if ok else "FAIL"
        extra = []
        if row["red_flag"]:
            extra.append("RED")
        if row["phase_week_mismatch"]:
            extra.append("MISMATCH")
        if row["iterations"] and row["iterations"] > 1:
            extra.append(f"loop x{row['iterations']}")
        print(f"[{mark}] {meta['patient_id']} ({meta['test_intent']:<16}) "
              f"expect={meta['expected_status']:<24} got={row['status']:<24} "
              f"{' '.join(extra)}")
    save_json(os.path.join(WORK, "batch_report.json"),
              {"total": len(results), "matched": n_pass, "results": results})
    print(f"\n{n_pass}/{len(results)} matched expected status → work/batch_report.json")
    sys.exit(0 if n_pass == len(results) else 1)


if __name__ == "__main__":
    main(sys.argv[1])
