"""SafeRx 공용 유틸. 전부 결정론적 — 랜덤·시간 의존 로직 금지 (generated_at 제외)."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
# SAFERX_WORK_DIR가 설정돼 있으면 그걸 쓴다 — 웹 서버(hooks_server.py)가 요청마다
# 격리된 임시 work 디렉토리를 지정하기 위함(동시 요청 충돌 방지). 없으면 ROOT/work.
WORK = os.environ.get("SAFERX_WORK_DIR") or os.path.join(ROOT, "work")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
    return path


def work_path(name):
    return os.path.join(WORK, name)


def get_path(obj, dotted):
    """'surgery_details.phase' 같은 점 표기 경로 조회. 없으면 None."""
    cur = obj
    for key in dotted.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


# ---------- 조건 매처 (rule_table의 patient_if / exercise_if) ----------

def _leaf(cond, obj):
    val = get_path(obj, cond["field"])
    op = cond["op"]
    ref = cond.get("value")
    if op == "eq":       return val == ref
    if op == "ne":       return val != ref
    if op == "in":       return val in ref
    if op == "gte":      return val is not None and val >= ref
    if op == "lte":      return val is not None and val <= ref
    if op == "gt":       return val is not None and val > ref
    if op == "lt":       return val is not None and val < ref
    if op == "is_null":  return val is None
    if op == "not_null": return val is not None
    raise ValueError(f"unknown op: {op}")


def match(cond, obj):
    """빈 조건({})은 항상 True. all/any 중첩 지원."""
    if not cond:
        return True
    if "all" in cond:
        return all(match(c, obj) for c in cond["all"])
    if "any" in cond:
        return any(match(c, obj) for c in cond["any"])
    return _leaf(cond, obj)


# ---------- phase 로직 (§4-G) ----------

def load_phase_map():
    return load_json(os.path.join(DATA, "week_phase_map.json"))


def phase_from_week(week, pmap=None):
    pmap = pmap or load_phase_map()
    for ph in pmap["phase_order"]:
        r = pmap["week_ranges"][ph]
        if week >= r["min_week"] and (r["max_week"] is None or week <= r["max_week"]):
            return ph
    return pmap["phase_order"][-1]


def effective_phase(week, declared_phase, pmap=None):
    """주차 유래 phase와 선언 phase 중 낮은 쪽 채택 (§4-G 보수 원칙)."""
    pmap = pmap or load_phase_map()
    order = pmap["phase_order"]
    derived = phase_from_week(week, pmap)
    lower = min(declared_phase, derived, key=order.index)
    return lower, derived, (declared_phase != derived)


def die(msg, code=1):
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(code)
