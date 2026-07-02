"""convert_personas.py — patients_soap_30.csv → 트리거 입력 JSON 30개 (코드).

매핑 규칙 (DECISIONS.md #11):
  surgery        : ACL_HS → "ACL_RECON" / 그 외(THA_POST 등) → 원문 유지
                   (GATE-01이 unsupported_surgery로 걸러내는 것이 기대 동작)
  week_post_op   : floor(post_op_weeks) — 소수 주차는 내림 (낮은 주차 = 낮은
                   phase = 보수적, §4-G 원칙과 방향 일치)
  age            : 그대로
  concomitant    : surgical_flags == "none" → null, 그 외 → 원문 문자열
                   (ACL의 meniscal_repair → §4-E manual review 기대)
  pain_nrs       : O_objective에서 "NRS n/10" 정규식 추출, 없으면 null
  swelling(bool) : O_objective의 부종 서술 분류 —
                   없음/경미 → false, 중등도/심함/증가 → true
                   ⚠️ 경계값 판단(팀 확인 필요: '경미'를 false로 둘지)
  notes          : S_subjective (환자 보고 원문) — Subjective 재료
  phase          : expected_phase 로마자 → PHASE_N. "VI"는 enum(I–V) 밖이므로
                   PHASE_V로 클램프 + note (해당 행은 스코프 밖 수술이라 무해)
  graft_type     : ACL_HS → "hamstring_autograft" / 그 외 → "n/a"
                   (GATE-01이 먼저 발화하므로 도달하지 않음)

usage: python3 convert_personas.py <csv> <out_dir>
"""
import csv, json, math, os, re, sys

ROMAN2PHASE = {"I": "PHASE_I", "II": "PHASE_II", "III": "PHASE_III",
               "IV": "PHASE_IV", "V": "PHASE_V"}


def parse_nrs(text):
    m = re.search(r"NRS\s*(\d+)\s*/\s*10", text or "")
    return int(m.group(1)) if m else None


def parse_swelling(text):
    """없음/경미 → False, 중등도/심함/증가 → True. 부종 언급 없으면 False."""
    t = text or ""
    m = re.search(r"부종\s*(없음|경미|중등도|심함|증가)", t)
    if not m:
        return False, "no_mention"
    grade = m.group(1)
    return grade in ("중등도", "심함", "증가"), grade


def convert_row(row):
    surgery = "ACL_RECON" if row["surgery_type"] == "ACL_HS" else row["surgery_type"]
    flags = row["surgical_flags"].strip()
    swell, grade = parse_swelling(row["O_objective"])
    roman = row["expected_phase"].strip()
    phase = ROMAN2PHASE.get(roman)
    notes_extra = []
    if phase is None:  # e.g. "VI" — enum(I–V) 밖
        phase = "PHASE_V"
        notes_extra.append(f"[converter] expected_phase {roman} → PHASE_V 클램프")
    inp = {
        "surgery": surgery,
        "week_post_op": int(math.floor(float(row["post_op_weeks"]))),
        "age": int(row["age"]),
        "concomitant_procedure": None if flags == "none" else flags,
        "pain_nrs": parse_nrs(row["O_objective"]),
        "swelling": swell,
        "notes": row["S_subjective"].strip().strip('"'),
        "surgery_details": {
            "phase": phase,
            "graft_type": "hamstring_autograft" if row["surgery_type"] == "ACL_HS" else "n/a",
        },
    }
    meta = {"patient_id": row["patient_id"], "test_intent": row["test_intent"],
            "expected_phase": row["expected_phase"], "swelling_grade": grade,
            "converter_notes": notes_extra}
    return inp, meta


def main(csv_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    index = []
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            inp, meta = convert_row(row)
            pid = meta["patient_id"]
            path = os.path.join(out_dir, f"{pid}.json")
            with open(path, "w", encoding="utf-8") as g:
                json.dump(inp, g, ensure_ascii=False, indent=2)
            # 파이프라인 기대 결과 (배치 검증용)
            if inp["surgery"] != "ACL_RECON":
                expect = "unsupported_surgery"
            elif inp["concomitant_procedure"] is not None:
                expect = "manual_review_required"
            else:
                expect = "ready_for_reporter"
            meta["expected_status"] = expect
            meta["input_file"] = f"{pid}.json"
            index.append(meta)
    with open(os.path.join(out_dir, "_index.json"), "w", encoding="utf-8") as g:
        json.dump(index, g, ensure_ascii=False, indent=2)
    print(f"wrote {len(index)} persona inputs + _index.json → {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
