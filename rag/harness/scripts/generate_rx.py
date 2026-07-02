"""generate_rx.py — 처방 조립 (코드, LLM 아님). spec §4-A, §4-I, §5.

safety_checked == true 후보 중 priority 상위 5개를 선택하고, sets/reps/frequency/
intensity/rationale/source를 **라이브러리 값 그대로 복사**한다. 생성·변형 금지 —
이것이 §4-A(데이터 바운드)의 기계적 보장이자 dosage gap 봉합의 절반이다
(나머지 절반은 safety_judge completeness 모드의 재검증).

clamp가 적용된 후보는 intensity 서술에 제한 범위를 병기한다.

usage: python3 generate_rx.py
"""
import sys
from lib import load_json, save_json, work_path, die

N = 5


def main():
    cands = load_json(work_path("10_candidates.json"))
    safety = load_json(work_path("20_safety.json"))
    if safety.get("decision") != "approved":
        die(f"generate_rx requires approved gate (got {safety.get('decision')})")

    ok_names = {c["name_en"] for c in safety["exercises_checked"] if c["safety_checked"]}
    # 검색 순서(phase-distance 우선 정렬)를 보존한다 — priority 재정렬 금지.
    pool = [e for e in cands["candidates"] if e["name"]["en"] in ok_names]

    # ── 입력-결정론적 다양화 ──────────────────────────────────────────
    # 문제: 상위 5개 단순 컷은 (a) 같은 phase면 항상 동일한 5개, (b) 유사 근육군 편중.
    # 해법: target_muscle 그룹 간 라운드로빈으로 균형 잡힌 포트폴리오를 만들고,
    #       시작 그룹을 week_post_op에서 유도해 같은 phase라도 주차가 다르면
    #       조합이 달라지게 한다. 난수 없음 — 같은 입력이면 항상 같은 5개
    #       (spec 재현성 불변식 유지). 그룹 순서·그룹 내 순서 모두 결정론적.
    ctx = load_json(work_path("00_context.json"))
    groups, order = {}, []
    for e in pool:
        g = e.get("target_muscle", "etc")
        if g not in groups:
            groups[g] = []
            order.append(g)
    for e in pool:
        groups[e.get("target_muscle", "etc")].append(e)
    week = ctx.get("week_post_op", 0)
    if order:
        start = week % len(order)
        order = order[start:] + order[:start]
    # 그룹 내부도 주차 회전 — 같은 근육군 슬롯이 주차에 따라 다른 운동으로 순환
    # (예: 대퇴사두근 슬롯이 wk3 단축범위 → wk4 월싯 → wk5 레그프레스).
    # 역시 난수 없음: week의 순수 함수라 재현성 유지.
    for g in groups:
        if len(groups[g]) > 1:
            r = week % len(groups[g])
            groups[g] = groups[g][r:] + groups[g][:r]
    diversified, gi = [], 0
    while len(diversified) < len(pool) and any(groups[g] for g in order):
        g = order[gi % len(order)]
        if groups[g]:
            diversified.append(groups[g].pop(0))
        gi += 1
    pool = diversified

    if len(pool) < N:
        # 정확히 5개 불충족 → 재검색 필요 신호 (지어내지 않음, §4-A)
        save_json(work_path("40_prescription.json"),
                  {"exercises": [], "short": True, "available": len(pool)})
        print(f"STOP: only {len(pool)} safe candidates (<{N}) — re-search needed")
        sys.exit(14)

    exercises = []
    for e in pool[:N]:
        item = {
            "name": e["name"],
            "sets": e["dosage"]["sets"],
            "reps": e["dosage"]["reps"],
            "intensity": dict(e["dosage"]["intensity"]),
            "rationale": e["rationale"],
            "source": e["source"],
            "safety_checked": True,
            # completeness 재검증용 속성 (룰 매칭에 필요)
            "load_type": e["load_type"], "kinetic_chain": e["kinetic_chain"],
            "target_muscle": e["target_muscle"], "resisted": e["resisted"],
            "resisted_knee_flexion": e["resisted_knee_flexion"],
            "hamstring_load": e["hamstring_load"],
            "eccentric_hamstring": e["eccentric_hamstring"],
            "knee_flexion_max": e["knee_flexion_max"],
            "weight_bearing": e["weight_bearing"],
            "intensity_level": e["intensity_level"],
            "category": e["category"],
        }
        if e.get("knee_extension_end") is not None:
            item["knee_extension_end"] = e["knee_extension_end"]
        if e.get("clamped"):
            lim = ", ".join(e["clamped"])
            item["intensity"]["ko"] += f" (범위 제한: {lim})"
            item["intensity"]["en"] += f" (clamped: {lim})"
            item["clamped"] = e["clamped"]
        exercises.append(item)

    save_json(work_path("40_prescription.json"), {"exercises": exercises, "short": False})
    print(f"wrote work/40_prescription.json (exactly {N})")


if __name__ == "__main__":
    main()
