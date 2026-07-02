"""run_pipeline.py — 코드 구간 일괄 실행.

extract → red flag(통증·부종) 임계값 체크(결정론) → notes_screen(이진 신호만, 안전판정 아님)
→ retrieve → judge(safety) → [correct → retrieve → judge]×≤5 → generate → judge(completeness)

성공 시 상태 READY_FOR_REPORTER — 이후는 오케스트레이터(LLM)가
reporter-subagent → report_validate.py → report-judge-subagent 순으로 진행.

중단 상태는 work/99_status.json에 기록된다:
  unsupported_surgery / unsupported_case / manual_review_required /
  insufficient_evidence / failed(수동 검토) / ready_for_reporter

usage: python3 run_pipeline.py <trigger_input.json>
"""
import os, subprocess, sys
from lib import load_json, save_json, work_path, ROOT

MAX_ITER = 5
PY = sys.executable
SCRIPTS = os.path.join(ROOT, "scripts")

# 통증 NRS가 이 값 이상이거나 부종이 있으면 운동 자체를 추천하지 않고 PT에게 넘긴다(팀 결정).
# 예전엔 이걸 judge 단계의 REDFLAG-01(force_isometric)로 처리했는데, red flag 운동이
# 여러 개면 "위반 11건 이상 -> 즉시 failed" 카운팅에 걸려서 교정 기회도 못 얻고 죽는
# 버그가 있었다. 그래서 judge까지 가지도 않고 여기서 미리 걸러낸다 — REDFLAG-01 룰은
# 이제 도달 불가능해져서 rule_table.json에서 제거했다.
PAIN_DEFER_THRESHOLD = 4


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


def defer_to_pt(reason, quote=""):
    """운동 검색·판정을 건너뛰고 빈 처방으로 바로 리포트 단계로 넘긴다.
    안전 판정 자체는 건드리지 않는다 — SOAP(S/O/A)는 정상 생성된다."""
    save_json(work_path("40_prescription.json"), {
        "exercises": [], "short": False,
        "deferred_to_pt": True,
        "defer_reason": reason,
        "defer_quote": quote,
    })
    stop("ready_for_reporter", f"deferred_to_pt: {reason}")


def main(inp):
    rc = run("extract_redact.py", inp)
    if rc == 10:
        stop("unsupported_surgery")
    if rc == 11:
        stop("manual_review_required", "concomitant_procedure")
    if rc != 0:
        stop("error", f"extract_redact rc={rc}")

    ctx = load_json(work_path("00_context.json"))
    pain = ctx.get("pain_nrs")
    swelling = ctx.get("swelling")

    red_flag_reasons = []
    if pain is not None and pain >= PAIN_DEFER_THRESHOLD:
        red_flag_reasons.append(f"pain_nrs={pain} (임계값 {PAIN_DEFER_THRESHOLD} 이상)")
    if swelling:
        red_flag_reasons.append("swelling=true")

    if red_flag_reasons:
        defer_to_pt(" / ".join(red_flag_reasons) + " — red flag로 인한 운동 추천 보류")

    rc = run("notes_screen.py")
    if rc != 0 and rc != 16:
        stop("error", f"notes_screen rc={rc}")

    if rc == 16:
        screen = load_json(work_path("05_notes_screen.json"))
        defer_to_pt(screen.get("reason", ""), screen.get("quote", ""))

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
