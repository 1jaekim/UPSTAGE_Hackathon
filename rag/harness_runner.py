# saferx-v2 하네스 파이프라인을 요청마다 격리된 임시 작업공간에서 실행하는 오케스트레이터.
# harness/scripts/run_pipeline.py(결정론 구간) 실행 -> ready_for_reporter면
# reporter.py(LLM 서술) -> report_validate.py(Gate 3, 기계 검증) -> report_judge.py
# (Gate 2, LLM) 순서로 진행. Gate 3/Gate 2 실패 시 최대 3회까지 reporter를 재시도한다.
#
# 반환 계약:
# {
#   "status": "ready_for_reporter" | "unsupported_surgery" | "manual_review_required"
#             | "insufficient_evidence" | "failed",
#   "detail": "string",
#   "report": {...} | null   # status == "ready_for_reporter"일 때만 채워짐 (spec.md §5 스키마)
# }

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent.parent / "saferx-v2"
HARNESS_SCRIPTS = HARNESS_ROOT / "scripts"
PY = sys.executable
MAX_REPORT_ATTEMPTS = 3


def _run_script(script_name: str, work_dir: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "SAFERX_WORK_DIR": str(work_dir)}
    return subprocess.run(
        [PY, str(HARNESS_SCRIPTS / script_name), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _pipeline_meta(work_dir: Path) -> dict:
    safety_path = work_dir / "20_safety.json"
    if not safety_path.exists():
        return {"correction_used": False, "iterations": 0}
    safety = _read_json(safety_path)
    iterations = safety.get("iteration", 1)
    return {"correction_used": iterations > 1, "iterations": iterations}


def run_harness_pipeline(payload: dict, judge_mode: str | None = None) -> dict:
    """judge_mode:
      - None or "split": 현행 아키텍처 — reporter LLM과 report-judge LLM 분리
      - "combined": 한 LLM 호출로 SOAP 작성 + 자기 판정을 동시 수행 (실험용)
    환경변수 SAFERX_JUDGE_MODE로도 지정 가능."""
    mode = judge_mode or os.environ.get("SAFERX_JUDGE_MODE") or "split"
    work_dir = Path(tempfile.mkdtemp(prefix="saferx_"))
    record_id = f"rec_{uuid.uuid4().hex[:8]}"
    try:
        input_path = work_dir / "input.json"
        input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        deterministic = _run_script("run_pipeline.py", work_dir, str(input_path))
        status_path = work_dir / "99_status.json"
        if not status_path.exists():
            return {
                "status": "failed",
                "detail": f"pipeline crashed before writing status: {deterministic.stderr[-500:]}",
                "report": None,
            }

        status_doc = _read_json(status_path)
        status = status_doc["status"]
        meta = _pipeline_meta(work_dir)
        meta["judge_mode"] = mode
        if status != "ready_for_reporter":
            return {"status": status, "detail": status_doc.get("detail", ""), "report": None, **meta}

        fix_notes = None
        llm_calls = 0
        for _attempt in range(1, MAX_REPORT_ATTEMPTS + 1):
            if mode == "combined":
                # 한 콜에 작성 + 자기 판정
                args = ["--fix-notes", fix_notes] if fix_notes else []
                combined_run = _run_script("reporter_judge_combined.py", work_dir, *args)
                llm_calls += 1
                if combined_run.returncode not in (0, 1):
                    # 크래시(2 이상) → 재시도
                    fix_notes = f"combined.py crashed: {combined_run.stderr[-500:]}"
                    continue
                _run_script("report_validate.py", work_dir)
                validation = _read_json(work_dir / "55_validation.json")
                if not validation["pass"]:
                    fix_notes = "; ".join(f'{f["check"]}: {f["detail"]}' for f in validation["fails"])
                    continue
                verdict = _read_json(work_dir / "60_judge.json")
                if verdict.get("pass"):
                    report = _read_json(work_dir / "50_report.json")
                    report["report_meta"]["record_id"] = record_id
                    meta["llm_calls"] = llm_calls
                    return {"status": "ready_for_reporter", "detail": "", "report": report, **meta}
                fix_notes = verdict.get("notes", "combined self-judge rejected")
            else:
                # split(현행): reporter → validate → judge
                reporter_args = ["--fix-notes", fix_notes] if fix_notes else []
                reporter_run = _run_script("reporter.py", work_dir, *reporter_args)
                llm_calls += 1
                if reporter_run.returncode != 0:
                    fix_notes = f"reporter.py crashed: {reporter_run.stderr[-500:]}"
                    continue
                _run_script("report_validate.py", work_dir)
                validation = _read_json(work_dir / "55_validation.json")
                if not validation["pass"]:
                    fix_notes = "; ".join(f'{f["check"]}: {f["detail"]}' for f in validation["fails"])
                    continue
                judge_run = _run_script("report_judge.py", work_dir)
                llm_calls += 1
                verdict = _read_json(work_dir / "60_judge.json")
                if judge_run.returncode == 0 and verdict.get("pass"):
                    report = _read_json(work_dir / "50_report.json")
                    report["report_meta"]["record_id"] = record_id
                    meta["llm_calls"] = llm_calls
                    return {"status": "ready_for_reporter", "detail": "", "report": report, **meta}
                fix_notes = verdict.get("notes", "report rejected by gate-2 judge")

        meta["llm_calls"] = llm_calls
        return {
            "status": "manual_review_required",
            "detail": f"gate2_max_attempts_exceeded: {fix_notes}",
            "report": None,
            **meta,
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
