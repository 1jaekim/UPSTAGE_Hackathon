"""correct.py — 교정 루프 (코드, LLM 아님). spec §4-D, §6-1.

safety_judge가 rejected_loop일 때만 실행. violations[]의 correction_hint를
기계적으로 병합해 재검색 제약을 만든다:
  exclude          → 해당 운동 제외 + alternative_filter 병합
  clamp            → 속성 상한/하한 적용 (제외 대신 수정)
  force_isometric  → 모든 동적 운동 등척성 치환 (§4-D red flag)

usage: python3 correct.py
"""
import sys
from lib import load_json, save_json, work_path, die


def main():
    safety = load_json(work_path("20_safety.json"))
    if safety.get("decision") != "rejected_loop":
        die(f"correct.py must only run on rejected_loop (got {safety.get('decision')})")

    exclude, clamps, add_filters = set(), [], {}
    force_iso, reasons = False, []

    for v in safety["violations"]:
        hint = v.get("correction_hint", {})
        action = hint.get("action")
        reasons.append(f'{v["rule_id"]}({v["exercise"]})')
        if action == "exclude":
            exclude.add(v["exercise"])
            for k, val in hint.get("alternative_filter", {}).items():
                add_filters[k] = val  # 동일 키는 마지막 힌트가 우선 (결정론적: 룰 순서 고정)
        elif action == "clamp":
            clamps.append({"name_en": v["exercise"], "field": hint["clamp_field"],
                           "op": "min" if hint["clamp_field"].endswith("_end") else "max",
                           "value": hint["clamp_value"]})
        elif action == "force_isometric":
            force_iso = True

    out = {
        "iteration": safety.get("iteration", 1) + 1,
        "exclude": sorted(exclude),
        "add_filters": add_filters,
        "clamps": clamps,
        "force_isometric": force_iso,
        "reason": "; ".join(reasons),
    }
    save_json(work_path("30_correction.json"), out)
    print(f"wrote work/30_correction.json (iter {out['iteration']}, "
          f"exclude={len(exclude)}, clamps={len(clamps)}, force_iso={force_iso})")


if __name__ == "__main__":
    main()
