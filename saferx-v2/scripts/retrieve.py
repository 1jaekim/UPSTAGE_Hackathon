"""retrieve.py — 후보 운동 검색 (코드, LLM 아님).

역할 (spec §4-A, 데이터 바운드):
  - exercise_library.json에서 phase/graft 조건에 맞는 후보를 결정론적으로 필터.
  - 교정 패스(work/30_correction.json 존재 시): exclude / add_filters /
    force_isometric / clamp 를 적용.
  - 후보 부족(<5) 시 insufficient_evidence — 절대 지어내지 않음.
  - 무출처 항목 제외. 후보는 넉넉히(최대 10개) 반환.

설계 메모: 초기 검색은 red flag를 *선필터하지 않는다*. spec §4-D의 설계는
"동적 운동 auto-fail → corrector가 강제 치환"이므로, red-flag 처리는 Gate 1
판정 + 교정 루프가 담당한다 (판정 경로의 관측 가능성 유지, DECISIONS.md #4).

ChromaDB 훅: 프로덕션에서는 filter_candidates()를 ChromaDB 메타데이터 필터
쿼리로 교체하면 된다. 인터페이스(입출력 JSON)는 동일.

usage: python3 retrieve.py
"""
import os, sys
from lib import load_json, save_json, work_path, DATA, die

MAX_CANDIDATES = 10
MIN_REQUIRED = 5


def apply_correction_filters(exs, corr):
    excl = set(corr.get("exclude", []))
    exs = [e for e in exs if e["name"]["en"] not in excl]
    if corr.get("force_isometric"):
        exs = [e for e in exs if e["load_type"] == "isometric"]
    af = corr.get("add_filters", {})
    if "load_type_in" in af:
        exs = [e for e in exs if e["load_type"] in af["load_type_in"]]
    if "hamstring_load_in" in af:
        exs = [e for e in exs if e["hamstring_load"] in af["hamstring_load_in"]]
    if "kinetic_chain_in" in af:
        exs = [e for e in exs if e["kinetic_chain"] in af["kinetic_chain_in"]]
    if "intensity_level_in" in af:
        exs = [e for e in exs if e["intensity_level"] in af["intensity_level_in"]]
    if "resisted_knee_flexion" in af:
        exs = [e for e in exs if e["resisted_knee_flexion"] == af["resisted_knee_flexion"]]
    if "eccentric_hamstring" in af:
        exs = [e for e in exs if e["eccentric_hamstring"] == af["eccentric_hamstring"]]
    if "weight_bearing_in" in af:
        exs = [e for e in exs if e["weight_bearing"] in af["weight_bearing_in"]]
    if "category_not" in af:
        exs = [e for e in exs if e["category"] != af["category_not"]]
    # clamp: 속성값 상한 적용 (제외가 아니라 수정)
    for clamp in corr.get("clamps", []):
        for e in exs:
            if e["name"]["en"] == clamp["name_en"] and e.get(clamp["field"]) is not None:
                if clamp["op"] == "max" and e[clamp["field"]] > clamp["value"]:
                    e[clamp["field"]] = clamp["value"]
                    e.setdefault("clamped", []).append(f'{clamp["field"]}≤{clamp["value"]}')
                if clamp["op"] == "min" and e[clamp["field"]] < clamp["value"]:
                    e[clamp["field"]] = clamp["value"]
                    e.setdefault("clamped", []).append(f'{clamp["field"]}≥{clamp["value"]}')
    return exs


def main():
    ctx = load_json(work_path("00_context.json"))
    lib = load_json(os.path.join(DATA, "exercise_library.json"))

    # 기본 필터: phase 적합 + 출처 존재 (§4-A / GEN-01)
    exs = [dict(e) for e in lib["exercises"]
           if ctx["phase"] in e["phases"] and e.get("source")]

    corr_path = work_path("30_correction.json")
    iteration = 1
    if os.path.exists(corr_path):
        corr = load_json(corr_path)
        iteration = corr.get("iteration", 1)
        exs = apply_correction_filters(exs, corr)

    # 결정론적 정렬: phase 거리(현 단계 도입 운동 우선) → priority → name_en
    # min_phase 모델(해당 단계부터 허용)에서는 초기 운동이 영원히 후보로 남으므로,
    # 현 단계에 도입된 운동을 먼저 뽑아야 단계 적합 처방이 된다.
    ORDER = ["PHASE_I", "PHASE_II", "PHASE_III", "PHASE_IV", "PHASE_V"]
    cur = ORDER.index(ctx["phase"])
    def phase_dist(e):
        return cur - ORDER.index(e.get("min_phase", e["phases"][0]))
    exs.sort(key=lambda e: (phase_dist(e), e["priority"], e["name"]["en"]))
    exs = exs[:MAX_CANDIDATES]

    insufficient = len(exs) < MIN_REQUIRED
    out = {
        "iteration": iteration,
        "filters": {"phase": ctx["phase"], "graft_type": ctx["graft_type"]},
        "candidates": exs,
        "candidate_count": len(exs),
        "insufficient_evidence": insufficient,
    }
    save_json(work_path("10_candidates.json"), out)
    print(f"wrote work/10_candidates.json ({len(exs)} candidates, iter {iteration})")
    if insufficient:
        print("STOP: insufficient_evidence")
        sys.exit(12)


if __name__ == "__main__":
    main()
