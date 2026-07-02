"""extract_redact.py — 파이프라인 1단계 (코드, LLM 아님).

역할 (spec §3-2, §4-B/C/E/F/G):
  1. 구조화 필드 pass-through (§4-B) — 재파싱 금지
  2. notes 코드 기반 redaction (§4-F) — LLM에 원문이 닿기 *전에* 실행됨
  3. age → 연령대 일반화 (§4-F)
  4. scope gate: unsupported_surgery / concomitant_procedure (§3, §4-E)
  5. week↔phase 일관성 (§4-G): 낮은 phase 보수 채택 + 플래그
출력: work/00_context.json

usage: python3 extract_redact.py <trigger_input.json>
"""
import re, sys
from lib import load_json, save_json, work_path, effective_phase, die

# ---- redaction 패턴 (§4-F) ----
RE_RRN = re.compile(r"\b\d{6}[-‐–]\d{7}\b")                                   # 주민등록번호
RE_PHONE = re.compile(r"\b01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}\b"             # 휴대폰
                      r"|\b0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}\b")             # 지역번호
RE_INST = re.compile(r"[가-힣A-Za-z0-9]+(?:병원|의원|정형외과|재활의학과|한방병원|한의원|클리닉|보건소|센터)")
_SURNAMES = ("김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구민진지엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥인제모탁")
RE_NAME = re.compile(rf"[{_SURNAMES}][가-힣]{{1,2}}\s?(?:님|씨|환자분?|어르신)")

REQUIRED = ["surgery", "week_post_op", "age", "swelling", "notes", "surgery_details"]


def redact_notes(text):
    """정형 PII는 정규식으로 확정 마스킹. 이름은 '성+이름+호칭' 보수 패턴만 —
    한계: 호칭 없는 이름은 못 잡는다. 프로덕션에서는 NER 보강 필요 (README 참고)."""
    text = RE_RRN.sub("[주민번호]", text)
    text = RE_PHONE.sub("[전화번호]", text)
    text = RE_INST.sub("[기관명]", text)
    text = RE_NAME.sub("[이름]", text)
    return text


def age_band(age):
    if age < 10:
        return "0s"
    return f"{(age // 10) * 10}s"


def main(inp_path):
    inp = load_json(inp_path)

    missing = [k for k in REQUIRED if k not in inp]
    if missing:
        die(f"required fields missing: {missing}")

    # scope gate (§3, §4-E) — 여기서 걸리면 downstream 스킵
    flags = {"unsupported_surgery": False, "manual_review_required": False,
             "manual_review_reason": None, "phase_week_mismatch": False, "red_flag": False}

    if inp["surgery"] != "ACL_RECON":
        flags["unsupported_surgery"] = True
    if inp.get("concomitant_procedure") is not None:
        flags["manual_review_required"] = True
        flags["manual_review_reason"] = "concomitant_procedure"

    declared = inp["surgery_details"]["phase"]
    eff, derived, mismatch = effective_phase(inp["week_post_op"], declared)
    flags["phase_week_mismatch"] = mismatch

    pain = inp.get("pain_nrs")
    flags["red_flag"] = (pain is not None and pain >= 7) or inp["swelling"] is True

    ctx = {
        # pass-through (§4-B)
        "surgery": inp["surgery"],
        "week_post_op": inp["week_post_op"],
        "phase": eff,                      # 유효 phase (보수 채택 결과)
        "phase_declared": declared,
        "phase_derived_from_week": derived,
        "graft_type": inp["surgery_details"]["graft_type"],
        "pain_nrs": pain,
        "swelling": inp["swelling"],
        "concomitant_procedure": inp.get("concomitant_procedure"),
        # §4-F: 일반화·마스킹된 값만 downstream/LLM에 노출
        "age_band": age_band(inp["age"]),
        "notes_redacted": redact_notes(inp["notes"]),
        "flags": flags,
    }
    # §4-C: notes에서 판단 필드를 새로 만들지 않는다 — notes_redacted는 참고 서술 전용.

    out = save_json(work_path("00_context.json"), ctx)
    print(f"wrote {out}")
    if flags["unsupported_surgery"]:
        print("STOP: unsupported_surgery")
        sys.exit(10)
    if flags["manual_review_required"]:
        print("STOP: manual_review_required (concomitant_procedure)")
        sys.exit(11)
    # NRS ≥ 6 → 즉시 red_flag 종료 (운동 추천 금지). 부종 단독은 REDFLAG-01 룰이 downstream에서 처리.
    if pain is not None and pain >= 6:
        print(f"STOP: red_flag (pain_nrs={pain} >= 6)")
        sys.exit(15)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        die("usage: extract_redact.py <trigger_input.json>")
    main(sys.argv[1])
