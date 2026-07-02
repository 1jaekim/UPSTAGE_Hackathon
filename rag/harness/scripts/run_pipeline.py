"""run_pipeline.py — 코드 구간 일괄 실행 (LLM 개입 없음).

extract → retrieve → judge(safety) → [correct → retrieve → judge]×≤5
→ generate → judge(completeness)

성공 시 상태 READY_FOR_REPORTER — 이후는 오케스트레이터(LLM)가
reporter-subagent → report_validate.py → report-judge-subagent 순으로 진행.

중단 상태는 work/99_status.json에 기록된다:
  unsupported_surgery / manual_review_required / insufficient_evidence /
  failed(수동 검토) / ready_for_reporter

usage: python3 run_pipeline.py <trigger_input.json>
"""
import os, subprocess, sys
from lib import save_json, work_path, ROOT

MAX_ITER = 5
PY = sys.executable
SCRIPTS = os.path.join(ROOT, "scripts")


def run(script, *args):
    r = subprocess.run([PY, os.path.join(SCRIPTS, script), *args],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


def stop(status, detail=""):
    save_json(work_path("99_status.json"), {"status": status, "detail": detail})
    print(f"[pipeline] STATUS = {status} {detail}")
    sys.exit(0 if status == "ready_for_reporter" else 1)


def main(inp):
    rc = run("extract_redact.py", inp)
    if rc == 10:
        stop("unsupported_surgery")
    if rc == 11:
        stop("manual_review_required", "concomitant_procedure")
    if rc != 0:
        stop("error", f"extract_redact rc={rc}")

    for it in range(1, MAX_ITER + 2):
        rc = run("retrieve.py")
        if rc == 12:
            stop("insufficient_evidence")
        if rc != 0:
            stop("error", f"retrieve rc={rc}")

        rc = run("safety_judge.py", "--mode", "safety")
        if rc == 0:          # approved
            break
        if rc == 20:         # rejected_loop
            if it >= MAX_ITER:
                stop("failed", "max_iterations reached")
            rc2 = run("correct.py")
            if rc2 != 0:
                stop("error", f"correct rc={rc2}")
            continue
        if rc == 21:         # failed (≥11 hard)
            stop("failed", "hard_violations >= 11")
        if rc == 13:
            stop("unsupported_case", "input gate fired at judge")
        stop("error", f"safety_judge rc={rc}")

    rc = run("generate_rx.py")
    if rc == 14:
        stop("failed", "fewer than 5 safe candidates after loop")
    if rc != 0:
        stop("error", f"generate_rx rc={rc}")

    rc = run("safety_judge.py", "--mode", "completeness")
    if rc != 0:
        stop("failed", "completeness check failed")

    stop("ready_for_reporter")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: run_pipeline.py <trigger_input.json>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])
