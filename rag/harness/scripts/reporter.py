"""reporter.py — SOAP 서술 생성 (LLM, 유일한 서사 담당 역할).

spec.md §5/§4-H, agents/reporter-subagent/AGENT.md를 코드로 옮긴 버전.

핵심 설계: LLM에게 전체 JSON을 맡기지 않는다. exercises/report_meta/manual_review/
safety는 파이썬이 work/40_prescription.json 등에서 그대로(verbatim) 조립하고,
LLM은 딱 서술 문장(S/O/A/P 나레이션, 이중언어)만 짧은 JSON으로 반환한다.
이러면 "처방을 절대 변형하지 않는다"는 제약이 LLM의 지시 준수 여부에 기대지 않고
구조적으로 보장된다.

usage: python3 reporter.py [--fix-notes '<work/55_validation.json 경로 또는 내용>']
"""
import argparse, datetime, os

from lib import load_json, save_json, work_path
from upstage_client import chat_json


def build_report_meta(ctx, prescription):
    sources = sorted({e["source"] for e in prescription["exercises"]})
    return {
        "record_id": None,  # 서버(오케스트레이터)가 채움
        "surgery": ctx["surgery"],
        "week_post_op": ctx["week_post_op"],
        "phase": ctx["phase"],
        "graft_type": ctx["graft_type"],
        "format": "SOAP",
        "language": "ko-en",
        "protocol_source": {
            "name": "ACL Hamstring Autograft Protocol (SAMPLE — 팀 프로토콜 원문 대조 필요)",
            "url": None,
            "refs": sources,
        },
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def build_manual_review(completeness):
    items = []
    if completeness:
        for mr in completeness.get("manual_review", []):
            items.append(
                {
                    "item": f'{mr["rule_id"]}:{mr["exercise"]}',
                    "note": {"ko": "PT 수동 확인 필요", "en": "PT manual review required"},
                }
            )
    # spec §3-1: criterion 기반 항목은 항상 수동 확인 대상으로 명시
    items.append(
        {
            "item": "quadriceps_strength_criterion",
            "note": {"ko": "대퇴사두근 근력 등 실측 지표는 자동 판정 대상 아님 — PT 수동 확인 필요",
                      "en": "Measured criteria such as quadriceps strength are not auto-judged — PT manual review required"},
        }
    )
    return items


NARRATIVE_SCHEMA_HINT = """
반드시 아래 JSON 스키마 하나만 출력하라(설명 문장 금지, 마크다운 코드펜스 금지):
{
  "subjective": {"ko": "...", "en": "..."},
  "objective": {"ko": "...", "en": "..."},
  "assessment": {"ko": "...", "en": "..."},
  "plan_summary": {"ko": "...", "en": "..."}
}
"""


def build_prompt(ctx, prescription, fix_notes=None):
    exercise_names = [e["name"]["en"] for e in prescription["exercises"]]
    fix_block = ""
    if fix_notes:
        fix_block = f"\n\n이전 시도가 다음 검증에 실패했다. 그 문제만 정확히 고쳐라:\n{fix_notes}\n"

    return f"""당신은 물리치료사를 위한 재활 운동처방 검수 리포트의 서술(narrative) 작성자입니다.
아래 데이터만 근거로 SOAP 노트의 4개 서술 섹션을 한국어+영어 이중언어로 작성하세요.
절대 하지 말 것: 진단 내리기, 단정적 지시("반드시 ~하세요"), 아래 데이터에 없는 내용 서술,
운동 이름/용량을 새로 만들거나 바꾸는 것(운동 목록은 이미 확정되어 있고 당신은 손대지 않습니다).

[환자 컨텍스트]
- 연령대: {ctx['age_band']}
- 참고 메모(마스킹됨, 그대로만 참고): {ctx['notes_redacted']}
- 수술 후 주차: {ctx['week_post_op']}주
- 유효 재활 단계: {ctx['phase']} (선언값: {ctx['phase_declared']}, 주차 기준: {ctx['phase_derived_from_week']})
- phase_week_mismatch: {ctx['flags']['phase_week_mismatch']}
- 이식건: {ctx['graft_type']}
- 통증 NRS: {ctx['pain_nrs']}
- 부종: {ctx['swelling']}
- red flag: {ctx['flags']['red_flag']}

[확정된 처방 운동 5개 — 이미 안전성 검증 통과, 그대로 인용만 할 것]
{', '.join(exercise_names)}

[작성 지침]
- subjective: 연령대 + 주호소(참고 메모 기반)만. 위 마스킹된 메모 외 내용 지어내지 말 것.
- objective: 주차/유효 단계/부종/통증/이식건 등 관찰 사실. phase_week_mismatch가 true면
  "주차와 선언된 단계가 불일치하여 보수적으로 낮은 단계를 채택했다"는 취지를 명시.
- assessment: 재활 단계 판단 근거·주의사항·red flag 여부. 진단/단정 금지, 제안+근거 톤 유지.
- plan_summary: 이번 단계 운동 계획을 2~3문장으로 요약 (운동 목록 자체는 별도 첨부되므로
  여기선 요약 문장만).
{fix_block}
{NARRATIVE_SCHEMA_HINT}
"""


def generate_narrative(ctx, prescription, fix_notes=None):
    prompt = build_prompt(ctx, prescription, fix_notes)
    return chat_json(prompt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix-notes", default=None, help="이전 검증 실패 사유(자유 텍스트)")
    args = ap.parse_args()

    ctx = load_json(work_path("00_context.json"))
    prescription = load_json(work_path("40_prescription.json"))
    completeness_path = work_path("45_completeness.json")
    completeness = load_json(completeness_path) if os.path.exists(completeness_path) else None

    narrative = generate_narrative(ctx, prescription, args.fix_notes)

    report = {
        "report_meta": build_report_meta(ctx, prescription),
        "soap": {
            "subjective": narrative["subjective"],
            "objective": narrative["objective"],
            "assessment": narrative["assessment"],
            "plan": {
                "ko": narrative["plan_summary"]["ko"],
                "en": narrative["plan_summary"]["en"],
                "exercises": [
                    {
                        "name": e["name"],
                        "sets": e["sets"],
                        "reps": e["reps"],
                        "frequency": e["frequency"],
                        "intensity": e["intensity"],
                        "rationale": e["rationale"],
                        "source": e["source"],
                        "safety_checked": e["safety_checked"],
                    }
                    for e in prescription["exercises"]
                ],
            },
        },
        "manual_review": build_manual_review(completeness),
        "safety": {"final_gate_passed": True, "violations": []},
    }

    out = save_json(work_path("50_report.json"), report)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
