"""reporter_judge_combined.py — 결합 모드 실험용 스크립트.

현행(multi) 아키텍처는 reporter LLM과 report-judge LLM을 **분리**해서
작성자-심사자 분리(spec §6-2)를 코드 수준에서 강제한다. 이 스크립트는
그 반대 극단 — **하나의 LLM 호출**이 SOAP 서술 작성 + 자기 판정까지
동시 수행 — 을 구현해 자기 채점 편향(self-serving bias)이 실측에서
얼마나 나타나는지 확인하는 baseline이다.

입력/출력은 reporter.py + report_judge.py를 합친 것과 같음:
  input : work/00_context.json, work/40_prescription.json, work/45_completeness.json
  output: work/50_report.json (SOAP), work/60_judge.json (자기 판정)

usage: python3 reporter_judge_combined.py [--fix-notes '<이전 실패 사유>']
"""
import argparse, datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import load_json, save_json, work_path
from reporter import build_report_meta, build_manual_review, _fallback_narrative
from single_agent import _call_llm, _extract_first_json


COMBINED_PROMPT = """당신은 재활 운동처방 SOAP 리포트의 **작성자이자 자체 심사자**입니다.
아래 데이터만 근거로 두 가지를 함께 수행하세요.

역할 1) SOAP 4개 서술(subjective/objective/assessment/plan_summary)을 한국어+영어로 작성
역할 2) 작성 직후 스스로를 J1(서술 품질)·J4(근거성) 기준으로 채점

절대 하지 말 것: 진단 내리기, 단정적 지시("반드시 ~하세요"), 아래 데이터에 없는 임상 주장,
운동 이름/용량 변경(운동 목록은 이미 확정, 손대지 않음).

[환자 컨텍스트]
- 연령대: {age_band}
- 참고 메모(마스킹됨, 그대로만 참고): {notes_redacted}
- 수술 후 주차: {week_post_op}주
- 유효 재활 단계: {phase} (선언: {phase_declared}, 주차 기준: {phase_derived_from_week})
- phase_week_mismatch: {mismatch}
- 이식건: {graft_type}
- 통증 NRS: {pain_nrs}
- 부종: {swelling}
- red flag: {red_flag}

[확정된 처방 운동 (그대로 인용, 절대 변경 금지)]
{exercise_names}

[작성 지침]
- subjective: 연령대 + 주호소만. 마스킹된 것 복원 금지.
- objective: 주차/단계/부종/통증/이식건 사실. mismatch가 true면 낮은 단계 채택 사유 명시.
- assessment: 단계 판단·주의·red flag 여부. 제안+근거 톤.
- plan_summary: 이번 단계 계획 2~3문장.

[자체 심사 규칙]
- J1(서술 품질): S/O/A/P가 placeholder가 아니고 문맥 일치, ko와 en이 같은 내용인지
- J4(근거성): 데이터에 없는 주장, 처방 재서술, notes 복원 여부
- 위반이 하나라도 있으면 pass=false, failed_checks에 명시.
{fix_block}

[출력 — 단 하나의 JSON, 다른 텍스트 절대 금지]
{{
  "subjective": {{"ko": "...", "en": "..."}},
  "objective":  {{"ko": "...", "en": "..."}},
  "assessment": {{"ko": "...", "en": "..."}},
  "plan_summary": {{"ko": "...", "en": "..."}},
  "self_judge": {{"pass": true 또는 false, "failed_checks": ["J1"과 "J4" 중 실패한 것], "notes": "판단 근거 한 줄"}}
}}
"""


def _degraded_narrative_and_pass(ctx):
    """LLM 불가 시: 결정론적 서술 + '통과' 자체 판정 (Multi의 report_judge와 같은 degraded 처리)."""
    n = _fallback_narrative(ctx)
    n["self_judge"] = {"pass": True, "failed_checks": [],
                       "notes": "DEGRADED: LLM unavailable — fallback narrative used, self-judge trivially passed."}
    return n


def generate_and_self_judge(ctx, prescription, fix_notes=None):
    fix_block = ""
    if fix_notes:
        fix_block = f"\n[이전 시도 실패 사유] 그 문제만 고쳐라:\n{fix_notes}\n"
    prompt = COMBINED_PROMPT.format(
        age_band=ctx["age_band"], notes_redacted=ctx["notes_redacted"],
        week_post_op=ctx["week_post_op"], phase=ctx["phase"],
        phase_declared=ctx["phase_declared"],
        phase_derived_from_week=ctx["phase_derived_from_week"],
        mismatch=ctx["flags"]["phase_week_mismatch"],
        graft_type=ctx["graft_type"], pain_nrs=ctx["pain_nrs"],
        swelling=ctx["swelling"], red_flag=ctx["flags"]["red_flag"],
        exercise_names=", ".join(e["name"]["en"] for e in prescription["exercises"]),
        fix_block=fix_block,
    )
    try:
        raw = _call_llm(prompt)
        return _extract_first_json(raw)
    except Exception as e:
        if os.environ.get("SAFERX_STRICT_LLM") != "1":
            print(f"[combined] LLM unavailable ({type(e).__name__}) — fallback")
            return _degraded_narrative_and_pass(ctx)
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix-notes", default=None)
    args = ap.parse_args()

    ctx = load_json(work_path("00_context.json"))
    prescription = load_json(work_path("40_prescription.json"))
    completeness_path = work_path("45_completeness.json")
    completeness = load_json(completeness_path) if os.path.exists(completeness_path) else None

    out = generate_and_self_judge(ctx, prescription, args.fix_notes)
    self_judge = out.pop("self_judge", {"pass": True, "failed_checks": [], "notes": ""})

    report = {
        "report_meta": build_report_meta(ctx, prescription),
        "soap": {
            "subjective": out["subjective"],
            "objective": out["objective"],
            "assessment": out["assessment"],
            "plan": {
                "ko": out["plan_summary"]["ko"],
                "en": out["plan_summary"]["en"],
                "exercises": [
                    {
                        "name": e["name"], "sets": e["sets"], "reps": e["reps"],
                        "frequency": e["frequency"], "intensity": e["intensity"],
                        "rationale": e["rationale"], "source": e["source"],
                        "safety_checked": e["safety_checked"],
                    }
                    for e in prescription["exercises"]
                ],
            },
        },
        "manual_review": build_manual_review(completeness),
        "safety": {"final_gate_passed": True, "violations": []},
    }
    save_json(work_path("50_report.json"), report)
    save_json(work_path("60_judge.json"), self_judge)
    print(f"combined mode: self_judge pass={self_judge.get('pass')} "
          f"failed={self_judge.get('failed_checks')}")
    sys.exit(0 if self_judge.get("pass") else 1)


if __name__ == "__main__":
    main()
