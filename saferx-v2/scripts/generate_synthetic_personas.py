"""generate_synthetic_personas.py — ACL 페르소나 표본 확장 (결정론 생성).

기존 팀 페르소나 9명(P001~P009) 이후에 P031부터 합성 페르소나를 추가한다.
결정론적 랜덤 시드(seed=42)로 재현 가능. 실제 임상 데이터 아님 — 스펙 규칙
커버리지 확대용.

카테고리별 배정:
  15명 normal (phase I~V 골고루)
   8명 red_flag (NRS 6~9)
   5명 concomitant (manual_review_required)
   3명 non-hamstring graft (unsupported_case)
  10명 boundary/trap_target/time_vs_criteria/meta_rule

총 41명 → 기존 9명 합쳐 ACL 유효 표본 50명.

usage: python3 saferx-v2/scripts/generate_synthetic_personas.py
"""
import json, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS = os.path.join(ROOT, "samples", "personas")
INDEX = os.path.join(PERSONAS, "_index.json")

random.seed(42)  # 재현성

# phase별 notes 뱅크 (자연스러운 한국어 재활 호소)
NOTES_BANK = {
    "PHASE_I": [
        "무릎이 뻣뻣하고 굽히기 힘들어요. 지금 할 수 있는 운동을 알려주세요.",
        "수술 후 통증이 남아있고 계단 오를 때 불안해요.",
        "붓기가 아직 있어서 무릎을 완전히 펴기 어렵습니다.",
        "다리 근력이 빠진 느낌인데 안전한 운동이 뭐가 있을까요?",
        "물리치료 사이에 집에서 할 수 있는 운동을 원해요.",
    ],
    "PHASE_II": [
        "걷는 건 편해졌는데 계단이 여전히 무섭습니다.",
        "재활 병원 다니고 있고 다음 단계 운동으로 넘어가고 싶어요.",
        "무릎 앞쪽이 뻐근한 느낌이 남아있어요.",
        "구부리기 각도가 조금씩 늘고 있는데 더 빨리 회복하고 싶어요.",
        "근력 운동을 시작해도 되는지 궁금합니다.",
    ],
    "PHASE_III": [
        "쪼그려 앉기까지 가능해졌는데 저항 운동을 시작해도 될지 궁금해요.",
        "가벼운 조깅을 하고 싶은데 아직 이른가요?",
        "런지나 스쿼트를 해도 되는지 알려주세요.",
        "일상 활동은 다 되는데 스포츠 복귀가 걱정입니다.",
    ],
    "PHASE_IV": [
        "복귀 훈련을 시작하려는데 어떤 운동이 안전한가요?",
        "축구 복귀를 목표로 하는데 지금 단계에서 뭘 해야 할까요?",
        "점프나 방향 전환 훈련을 넣고 싶어요.",
        "근력은 회복됐는데 민첩성이 걱정입니다.",
    ],
    "PHASE_V": [
        "스포츠 복귀 직전인데 마지막 점검이 필요해요.",
        "이미 러닝은 하고 있고 컨택 스포츠 복귀 준비 중입니다.",
        "재부상 예방을 위한 강화 운동을 원해요.",
    ],
}

RED_FLAG_NOTES = [
    "통증이 심해서 밤에 잠을 못 자요.",
    "무릎이 붓고 열이 나는 것 같습니다.",
    "재활 중에 통증이 오히려 심해졌어요.",
    "걸을 때마다 무릎이 시큰거리고 아파요.",
    "붓기가 다시 심해지고 통증이 강해졌습니다.",
]

CONCOMITANT_NOTES = [
    "반월판 봉합도 같이 받았습니다. 어떤 운동을 해도 될까요?",
    "연골 손상 수술을 병행해서 재활이 조심스러워요.",
    "다른 술식도 함께 받아서 물리치료사와 상의가 필요합니다.",
    "복합 손상이라 회복이 더디는 것 같습니다.",
    "동반 시술 때문에 일반 재활 프로토콜과 다르다고 들었어요.",
]

CONCOMITANT_TYPES = ["meniscal_repair", "cartilage_repair", "MCL_repair",
                     "PCL_reconstruction", "meniscectomy"]

# phase↔주차 매핑 (spec §4-G 참고)
PHASE_WEEK_RANGE = {
    "PHASE_I":   (0, 2),
    "PHASE_II":  (3, 6),
    "PHASE_III": (7, 12),
    "PHASE_IV":  (13, 24),
    "PHASE_V":   (25, 52),
}


def pick_notes(phase):
    return random.choice(NOTES_BANK.get(phase, NOTES_BANK["PHASE_II"]))


def base_persona(phase, week=None, nrs=None, swelling=None, age=None,
                 graft="hamstring_autograft", concomitant=None, notes=None):
    if week is None:
        wmin, wmax = PHASE_WEEK_RANGE[phase]
        week = random.randint(wmin, wmax)
    if nrs is None:
        nrs = random.randint(0, 4)  # 정상 범위
    if swelling is None:
        swelling = random.random() < 0.3
    if age is None:
        age = random.randint(15, 55)
    if notes is None:
        notes = pick_notes(phase)
    return {
        "surgery": "ACL_RECON",
        "week_post_op": week,
        "age": age,
        "concomitant_procedure": concomitant,
        "pain_nrs": nrs,
        "swelling": swelling,
        "notes": notes,
        "surgery_details": {"phase": phase, "graft_type": graft},
    }


def make_personas():
    out = []

    # ------- 15명 normal (phase I~V 골고루) -------
    normal_phases = ["PHASE_I"] * 3 + ["PHASE_II"] * 3 + ["PHASE_III"] * 3 + \
                    ["PHASE_IV"] * 3 + ["PHASE_V"] * 3
    for phase in normal_phases:
        out.append({"persona": base_persona(phase), "test_intent": "normal",
                    "expected_phase": phase[-1] if phase[-1].isalpha() else phase[6:],
                    "swelling_grade": "-"})

    # ------- 8명 red_flag (NRS 6~9) -------
    for _ in range(8):
        phase = random.choice(["PHASE_I", "PHASE_II", "PHASE_III"])
        nrs = random.randint(6, 9)
        notes = random.choice(RED_FLAG_NOTES)
        out.append({"persona": base_persona(phase, nrs=nrs, swelling=True, notes=notes),
                    "test_intent": "trap_target", "expected_phase": "-", "swelling_grade": "심함"})

    # ------- 5명 concomitant (manual_review) -------
    for _ in range(5):
        phase = random.choice(["PHASE_II", "PHASE_III"])
        conc = random.choice(CONCOMITANT_TYPES)
        notes = random.choice(CONCOMITANT_NOTES)
        out.append({"persona": base_persona(phase, concomitant=conc, notes=notes),
                    "test_intent": "meta_rule", "expected_phase": "-", "swelling_grade": "-"})

    # ------- 3명 non-hamstring graft (unsupported_case) -------
    for graft in ["patellar_tendon_autograft", "allograft", "quadriceps_tendon_autograft"]:
        phase = random.choice(["PHASE_II", "PHASE_III"])
        out.append({"persona": base_persona(phase, graft=graft),
                    "test_intent": "trap_target", "expected_phase": "-", "swelling_grade": "-"})

    # ------- 10명 boundary / trap_target / time_vs_criteria -------
    # 4 boundary — 임계치 근처
    out.append({"persona": base_persona("PHASE_I", week=2, nrs=5, swelling=True),
                "test_intent": "boundary", "expected_phase": "I", "swelling_grade": "경미"})
    out.append({"persona": base_persona("PHASE_II", week=6, nrs=5, swelling=False),
                "test_intent": "boundary", "expected_phase": "II", "swelling_grade": "-"})
    out.append({"persona": base_persona("PHASE_III", week=12, nrs=3),
                "test_intent": "boundary", "expected_phase": "III", "swelling_grade": "-"})
    out.append({"persona": base_persona("PHASE_IV", week=13),
                "test_intent": "boundary", "expected_phase": "IV", "swelling_grade": "-"})
    # 3 time_vs_criteria — 주차/phase 불일치
    out.append({"persona": base_persona("PHASE_III", week=4),  # 선언 III인데 주차는 II
                "test_intent": "time_vs_criteria", "expected_phase": "II", "swelling_grade": "-"})
    out.append({"persona": base_persona("PHASE_IV", week=8),   # 선언 IV, 주차 III
                "test_intent": "time_vs_criteria", "expected_phase": "III", "swelling_grade": "-"})
    out.append({"persona": base_persona("PHASE_V", week=20),   # 선언 V, 주차 IV
                "test_intent": "time_vs_criteria", "expected_phase": "IV", "swelling_grade": "-"})
    # 3 trap_target — 붓기 있지만 NRS 낮음, red_flag 아님
    out.append({"persona": base_persona("PHASE_II", nrs=3, swelling=True),
                "test_intent": "trap_target", "expected_phase": "II", "swelling_grade": "경미"})
    out.append({"persona": base_persona("PHASE_III", nrs=4, swelling=True),
                "test_intent": "trap_target", "expected_phase": "III", "swelling_grade": "경미"})
    out.append({"persona": base_persona("PHASE_I", nrs=5, swelling=False),
                "test_intent": "trap_target", "expected_phase": "I", "swelling_grade": "-"})

    return out


def main():
    idx = json.load(open(INDEX))
    max_id = max(int(e["patient_id"][1:]) for e in idx)
    start = max(31, max_id + 1)  # P031부터

    new = make_personas()
    added = []
    for i, entry in enumerate(new):
        pid = f"P{start + i:03d}"
        input_file = f"{pid}.json"
        path = os.path.join(PERSONAS, input_file)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry["persona"], f, ensure_ascii=False, indent=2)
        idx.append({
            "patient_id": pid,
            "test_intent": entry["test_intent"],
            "expected_phase": entry["expected_phase"],
            "swelling_grade": entry["swelling_grade"],
            "converter_notes": ["synthetic (generate_synthetic_personas.py, seed=42)"],
            "expected_status": None,  # gold은 build_dataset.py에서 결정론적으로 재계산
            "input_file": input_file,
        })
        added.append(pid)

    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)

    print(f"generated {len(added)} synthetic personas: {added[0]}..{added[-1]}")
    print(f"updated _index.json (total = {len(idx)} entries)")
    print()
    print("다음 단계:")
    print("  python3 saferx-v2/eval/build_dataset.py     # gold 재계산")
    print("  python3 saferx-v2/scripts/eval_f1.py --mode multi --acl-only")
    print("  python3 saferx-v2/scripts/eval_f1.py --mode single --acl-only")


if __name__ == "__main__":
    main()
