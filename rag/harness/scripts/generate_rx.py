"""generate_rx.py — 처방 조립 (코드, LLM 아님). spec §4-A, §4-I, §5.

safety_checked == true 후보 풀(최대 10개)에서 3개를 골라, rationale/source를
**라이브러리 값 그대로 복사**한다. 생성·변형 금지 — §4-A(데이터 바운드)의 기계적 보장.

3개 선택은 "환자 데이터 해시를 시드로 쓰는 결정론적 의사난수 조합 선택"이다:
  - 같은 환자 입력(주차/단계/이식건/통증/부종/연령대) -> 항상 같은 시드 -> 항상 같은 3개
    (재현성 성공기준 3 유지 — 진짜 랜덤이 아니라 입력의 순수 함수).
  - 다른 환자 -> 다른 시드 -> 후보 풀 안에서 다른 3개 조합이 나올 수 있음
    (매번 ID 정렬 앞 5개만 나오는 획일적인 결과 방지, 후보 풀이 작은 초기 단계에서도
    조합 수(nCk)가 늘어나 다양성이 커짐).
이 선택 로직은 안전성 판정과 무관하다 — 안전하지 않은 운동은 애초에 이 함수에
전달되는 pool에 들어오지 않는다(safety_checked 필터가 먼저 적용됨).

세트·반복·빈도(dosage)는 이 시스템이 정하지 않는다 — 그건 담당 물리치료사가 환자
상태를 보고 정할 몫이라, 애초에 처방 항목에 포함시키지 않는다(팀 결정).

clamp가 적용된 후보는 note에 제한 범위를 병기한다.

usage: python3 generate_rx.py
"""
import hashlib
import random
import sys

from lib import load_json, save_json, work_path, die

N = 3


def _selection_seed(ctx: dict) -> int:
    """환자의 구조화 필드만으로 만든 고정 시드. notes 등 자유텍스트는 안 씀(§4-C 원칙 유지)."""
    key = "|".join(str(ctx.get(k)) for k in
                    ("week_post_op", "phase", "graft_type", "pain_nrs", "swelling", "age_band"))
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)


def main():
    ctx = load_json(work_path("00_context.json"))
    cands = load_json(work_path("10_candidates.json"))
    safety = load_json(work_path("20_safety.json"))
    if safety.get("decision") != "approved":
        die(f"generate_rx requires approved gate (got {safety.get('decision')})")

    ok_names = {c["name_en"] for c in safety["exercises_checked"] if c["safety_checked"]}
    pool = [e for e in cands["candidates"] if e["name"]["en"] in ok_names]

    if len(pool) < N:
        # 정확히 N개 불충족 → 재검색 필요 신호 (지어내지 않음, §4-A)
        save_json(work_path("40_prescription.json"),
                  {"exercises": [], "short": True, "available": len(pool)})
        print(f"STOP: only {len(pool)} safe candidates (<{N}) — re-search needed")
        sys.exit(14)

    rng = random.Random(_selection_seed(ctx))
    selected = rng.sample(pool, N)
    selected.sort(key=lambda e: e["name"]["en"])  # 화면 표시 순서만 고정(선택 자체는 이미 끝남)

    exercises = []
    for e in selected:
        item = {
            "name": e["name"],
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
            item["note"] = {"ko": f"범위 제한: {lim}", "en": f"clamped: {lim}"}
            item["clamped"] = e["clamped"]
        exercises.append(item)

    save_json(work_path("40_prescription.json"), {"exercises": exercises, "short": False})
    print(f"wrote work/40_prescription.json (exactly {N})")


if __name__ == "__main__":
    main()
