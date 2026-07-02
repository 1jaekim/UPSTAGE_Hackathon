"""notes_screen.py — 특이사항(notes) 자유텍스트 안전 신호 감지 (LLM, 이진 스위치 전용).

이 스크립트가 하지 않는 것: "어떤 운동을 빼라/넣어라"를 판단하지 않는다. 안전 판정은
여전히 rule_table.json 대조(safety_judge.py)만 담당한다.

이 스크립트가 하는 것: notes에 "구조화된 필드(수술명/주차/이식건/통증/부종/동반술식)로는
포착 안 되는, 재활 안전에 영향 줄 만한 내용"이 있는지 이진(true/false)으로만 판단한다.
true면 무조건 manual_review_required로 에스컬레이션한다 — 하류 동작이 항상 고정이므로
LLM의 표현이 매번 조금씩 달라져도 파이프라인의 재현성(같은 입력 → 같은 상태)은 안 깨진다.

fail-safe 정책:
  - notes가 비어있으면 LLM 호출 없이 concern=False로 즉시 통과(비용·지연 절약).
  - LLM 호출 자체가 실패하면 "확인 못 했다"는 뜻이므로 안전하게 concern=True 처리.

usage: python3 notes_screen.py
"""
import sys

from lib import load_json, save_json, work_path
from upstage_client import chat_json

PROMPT_TMPL = """당신은 재활 운동처방 안전성 스크리닝 담당자입니다. 당신의 역할은 딱 하나,
"이 특이사항 텍스트 안에 아래 하네스가 구조화된 필드로는 알 수 없는, 재활 운동 안전성
판정에 영향을 줄 수 있는 내용이 있는가?"만 판단하는 것입니다. 절대 어떤 운동이 안전한지/
위험한지는 판단하지 마세요 — 그건 이 시스템의 다른 결정론적 규칙 엔진이 처리합니다.

이미 구조화된 필드로 별도 처리되므로 신경 쓰지 않아도 되는 것: 수술명, 회복 주차,
이식건 종류, 통증 수준(NRS), 부종 여부, 동반 수술 여부.

플래그를 켜야 하는 예: 복용 중인 약물(특히 항응고제·스테로이드·면역억제제), 유전 질환·
결합조직 질환(예: 엘러스-단로스 증후군), 이번 수술과 무관한 다른 부위의 부상·질환
(예: 발목 인대 손상, 허리 디스크), 선천적 신체 구조 이상, 임신 여부, 그 외 일반적인
재활 계획을 바꿀 만한 의학적 사실.

플래그를 켜면 안 되는 예: 단순 감정 표현("무섭다", "빨리 낫고 싶다"), 이미 구조화 필드로
들어온 내용의 반복(통증/부종 재언급), 안전과 무관한 일상 서술, 빈 내용.

[특이사항 텍스트 (마스킹됨)]
{notes}

반드시 아래 JSON 스키마 하나만 출력하라(설명 문장 금지, 마크다운 코드펜스 금지):
{{"concern": true 또는 false, "reason": "왜 그렇게 판단했는지 한 줄", "quote": "해당 원문 일부 또는 빈 문자열"}}
"""


def main():
    ctx = load_json(work_path("00_context.json"))
    notes = (ctx.get("notes_redacted") or "").strip()

    if not notes:
        save_json(work_path("05_notes_screen.json"), {"concern": False, "reason": "notes 비어있음", "quote": ""})
        print("notes_screen: notes 비어있음 -> concern=False (LLM 호출 스킵)")
        sys.exit(0)

    try:
        result = chat_json(PROMPT_TMPL.format(notes=notes))
    except Exception as e:
        result = {
            "concern": True,
            "reason": f"스크리닝 호출 실패로 안전하게 확인 필요 처리: {type(e).__name__}",
            "quote": "",
        }

    save_json(work_path("05_notes_screen.json"), result)
    print(f"notes_screen: concern={result.get('concern')} reason={result.get('reason')}")
    sys.exit(16 if result.get("concern") else 0)


if __name__ == "__main__":
    main()
