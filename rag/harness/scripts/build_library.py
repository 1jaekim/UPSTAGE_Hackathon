"""build_library.py — exercise_movement_map.csv (+sources.csv) → data/exercise_library.json

팀 제작 30개 운동 움직임 맵을 파이프라인 라이브러리로 변환한다 (코드, 재실행 가능).
원본(native) 필드는 전부 보존하고, 룰 엔진이 쓰는 파생 필드를 명시 규칙으로 생성한다.

파생 규칙 (DECISIONS.md #12):
  phases              : min_phase → [min_phase .. PHASE_V] (해당 단계부터 허용 모델)
  load_type           : contraction_type isometric → isometric, 그 외 → dynamic
  kinetic_chain       : open→OKC, closed→CKC, isometric→none
  target_muscle       : joint_motion 매핑 (knee extension→quadriceps 등)
  resisted            : load_source ∈ {machine, band, external_free}
  resisted_knee_flexion: motion에 knee flexion 포함 ∧ graft_site Y ∧ (resisted ∨ eccentric)
  eccentric_hamstring : contraction eccentric ∧ graft_site Y
  hamstring_load      : graft N→none / Y: eccentric→high, machine·external→medium, else low
  knee_flexion_max    : primary_joint==knee이면 rom_max_deg, 아니면 0 (NaN→0)
  knee_extension_end  : OKC 저항성 무릎신전에서 rom_min_deg (OKC-02 clamp 대상)
  intensity_level     : acl_strain_level 프록시 (⚠️개념 상이 — 팀 확인)
  weight_bearing      : 이름·모션 기반 (single-leg/step/lunge/drill → single_leg_*)
  category            : plyometric/agility/balance/rom/circulation/endurance/strength
  priority            : exercise_id 숫자 (결정론적)
  dosage              : ⚠️ 원본에 없음 → 전 항목 placeholder (팀 확정 필요)
  rationale.ko        : phase_rationale 원문 / .en: 축어 번역
  source              : source 태그 (상세는 data/sources.json)

usage: python3 build_library.py <movement_csv> <sources_csv>
"""
import csv, json, math, os, re, sys

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PHASES = ["PHASE_I", "PHASE_II", "PHASE_III", "PHASE_IV", "PHASE_V"]
R2P = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4}

MUSCLE = {"knee extension": "quadriceps", "knee flexion": "hamstring",
          "knee flexion + extension": "global_lower_limb",
          "knee multiplanar": "global_lower_limb", "knee rotation": "global_lower_limb",
          "knee stabilization": "global_lower_limb",
          "hip flexion": "hip_flexors", "hip abduction": "hip_abductors",
          "hip external rotation": "hip_external_rotators", "hip extension": "gluteals",
          "ankle dorsiflexion + plantarflexion": "calf", "ankle plantarflexion": "calf"}

RATIONALE_EN = {
 "EX001": "Isometric work permitted immediately post-op",
 "EX002": "Immediate use for circulation",
 "EX003": "Permitted when no extension lag",
 "EX004": "Phase I flexion limited to 90°",
 "EX005": "Early unresisted active flexion permitted",
 "EX006": "Early permitted — low ACL load",
 "EX007": "Early permitted — low ACL load",
 "EX008": "Low-load OKC in the terminal-extension arc",
 "EX009": "Phase II CKC within safe arc",
 "EX010": "Phase II CKC isometric hold",
 "EX011": "Phase II CKC; arc restricted by rule table",
 "EX012": "Phase II CKC; load adjusted by step height",
 "EX013": "ROM recovery plus aerobic conditioning",
 "EX014": "Phase II proprioceptive training",
 "EX015": "Bilateral-support CKC, low donor-site load",
 "EX016": "Weight-bearing closed-chain terminal extension",
 "EX017": "Deep-flexion progression stage",
 "EX018": "Caution with anterior-shear angles",
 "EX019": "Eccentric-control progression",
 "EX020": "Unilateral-loading progression",
 "EX021": "Resisted hamstring work from 12 weeks",
 "EX022": "OKC from 12 weeks; rule table restricts to 90–40°",
 "EX023": "Moderate eccentric hamstring loading",
 "EX024": "Dynamic proprioception progression",
 "EX025": "Posterior-chain strengthening",
 "EX026": "Full-range high load restricted to 6–9 months",
 "EX027": "High-load eccentric; late stage for HS autograft",
 "EX028": "Plyometrics from Phase IV",
 "EX029": "Deceleration / change-of-direction sport preparation",
 "EX030": "Return-to-sport rotational loading",
}

DOSAGE_PLACEHOLDER = {
    "sets": 3, "reps": 10,
    "frequency": {"ko": "1일 1회 (임시값)", "en": "Daily (placeholder)"},
    "intensity": {"ko": "통증 없는 범위 — 용량 임시값, 팀 확정 필요",
                  "en": "Pain-free range — dosage placeholder, team to finalize"},
}


def f2i(v, default=0):
    try:
        x = float(v)
        return default if math.isnan(x) else int(x)
    except (TypeError, ValueError):
        return default


def category(r):
    en = r["exercise_name_en"].lower()
    if "jump" in en or "hop" in en:
        return "plyometric"
    if "agility" in en or "cutting" in en or "pivot" in en or "deceleration" in en:
        return "agility"
    if "balance" in en or "stance" in en:
        return "balance"
    if r["exercise_id"] == "EX002":
        return "circulation"
    if r["exercise_id"] == "EX004":
        return "rom"
    if "bike" in en:
        return "endurance"
    return "strength"


def weight_bearing(r, kc):
    en = r["exercise_name_en"].lower()
    if kc != "CKC":
        return "none"
    if "single-leg stance" in en or ("balance" in en and "single" in en):
        return "single_leg_static"
    if any(k in en for k in ("step", "lunge", "single-leg", "agility", "cutting",
                             "deceleration", "pivot")):
        return "single_leg_dynamic"
    return "bilateral"


def convert(r):
    ex_id = r["exercise_id"]
    graft = r["graft_site_involved"].strip() == "Y"
    contraction = r["contraction_type"].strip()
    load_src = r["load_source"].strip()
    motion = r["joint_motion"].strip()
    kc = {"open": "OKC", "closed": "CKC", "isometric": "none"}[r["kinetic_chain"].strip()]
    resisted = load_src in ("machine", "band", "external_free")
    p0 = R2P[r["min_phase"].strip()]
    item = {
        "exercise_id": ex_id,
        "name": {"ko": r["exercise_name_ko"].strip(), "en": r["exercise_name_en"].strip()},
        "phases": PHASES[p0:],
        "min_phase": PHASES[p0],
        "priority": int(re.sub(r"\D", "", ex_id)),
        "category": category(r),
        "load_type": "isometric" if contraction == "isometric" else "dynamic",
        "kinetic_chain": kc,
        "target_muscle": MUSCLE.get(motion, "global_lower_limb"),
        "resisted": resisted,
        "resisted_knee_flexion": ("knee flexion" in motion and motion != "knee flexion + extension"
                                  and graft and (resisted or contraction == "eccentric")),
        "hamstring_load": ("none" if not graft else
                           "high" if contraction == "eccentric" else
                           "medium" if load_src in ("machine", "external_free") else "low"),
        "eccentric_hamstring": contraction == "eccentric" and graft,
        "knee_flexion_max": f2i(r["rom_max_deg"]) if r["primary_joint"] == "knee" else 0,
        "weight_bearing": None,  # 아래에서 채움 (kc 필요)
        "intensity_level": r["acl_strain_level"].strip(),
        "dosage": dict(DOSAGE_PLACEHOLDER),
        "dosage_status": "placeholder",
        "rationale": {"ko": r["phase_rationale"].strip(), "en": RATIONALE_EN[ex_id]},
        "source": r["source"].strip(),
        # native 필드 보존
        "native": {k: r[k] for k in ("primary_joint", "joint_motion", "rom_min_deg",
                                     "rom_max_deg", "load_source", "contraction_type",
                                     "strain_load_dependent", "graft_site_involved",
                                     "acl_strain_level", "injury_mechanism_risk",
                                     "notes", "status")},
    }
    item["weight_bearing"] = weight_bearing(r, kc)
    if kc == "OKC" and "knee extension" in motion and resisted:
        item["knee_extension_end"] = f2i(r["rom_min_deg"])  # OKC-02 clamp 대상
    return item


def main(mv_csv, src_csv):
    with open(mv_csv, encoding="utf-8-sig") as f:
        exercises = [convert(r) for r in csv.DictReader(f)]
    lib = {"library_id": "ACL-HS-EX-v2-team",
           "note": ("팀 제작 exercise_movement_map.csv 기반. 파생 필드 규칙은 "
                    "scripts/build_library.py 및 DECISIONS.md #12 참고. "
                    "⚠️ dosage는 원본에 없어 전 항목 placeholder — 팀 확정 필요. "
                    "status=draft: 임상 사용 전 검증 필요."),
           "exercises": exercises}
    out = os.path.join(DATA, "exercise_library.json")
    json.dump(lib, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    with open(src_csv, encoding="utf-8-sig") as f:
        sources = list(csv.DictReader(f))
    json.dump({"sources": sources},
              open(os.path.join(DATA, "sources.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"wrote {out} ({len(exercises)} exercises) + data/sources.json ({len(sources)} sources)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
