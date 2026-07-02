"""build_dataset.py — 페르소나 30명 + 원본 라벨(_index.json) + 현행 게이트 규칙으로
계산한 gold status를 하나의 자립형 평가 데이터셋으로 결합한다.

산출:
  saferx-v2/eval/dataset.jsonl     — 30줄, 각 줄이 하나의 테스트 케이스 (자립형)
  saferx-v2/eval/gold_labels.json  — {PID: gold_status} 요약 + 클래스 분포

규칙 변경 시(예: NRS 임계치 조정) 이 스크립트를 재실행해서 dataset을 갱신하면
평가 스크립트는 그대로 두고 정답만 새로 잡을 수 있다.

usage: python3 saferx-v2/eval/build_dataset.py
"""
import json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PERSONAS = os.path.join(ROOT, "samples", "personas")
INDEX = os.path.join(PERSONAS, "_index.json")


def gold_label(inp: dict) -> tuple[str, str]:
    """현행 파이프라인(extract_redact.py)의 게이트 순서를 그대로 옮긴 결정론적 정답 함수.
    반환: (gold_status, gold_reason)."""
    if inp.get("surgery") != "ACL_RECON":
        return "unsupported_surgery", f"surgery={inp.get('surgery')} != ACL_RECON"
    if inp["surgery_details"].get("graft_type") != "hamstring_autograft":
        return "unsupported_case", f"graft={inp['surgery_details'].get('graft_type')} != hamstring_autograft"
    if inp.get("concomitant_procedure") is not None:
        return "manual_review_required", f"concomitant={inp['concomitant_procedure']}"
    pain = inp.get("pain_nrs")
    if pain is not None and pain >= 6:
        return "red_flag", f"pain_nrs={pain} >= 6"
    return "ready_for_reporter", "게이트 통과 (ACL+hamstring+non-concomitant+NRS<6)"


def main():
    idx = json.load(open(INDEX))
    dataset_path = os.path.join(HERE, "dataset.jsonl")
    labels_path = os.path.join(HERE, "gold_labels.json")

    rows = []
    for entry in idx:
        pid = entry["patient_id"]
        inp = json.load(open(os.path.join(PERSONAS, entry["input_file"])))
        gold, reason = gold_label(inp)
        row = {
            "patient_id": pid,
            "test_intent": entry.get("test_intent"),
            "expected_phase": entry.get("expected_phase"),
            "swelling_grade": entry.get("swelling_grade"),
            "converter_notes": entry.get("converter_notes", []),
            "original_expected_status": entry.get("expected_status"),  # _index.json 원본 라벨
            "gold_status": gold,
            "gold_reason": reason,
            "input": inp,
        }
        rows.append(row)

    with open(dataset_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    dist = Counter(r["gold_status"] for r in rows)
    intent_by_class = {}
    for r in rows:
        intent_by_class.setdefault(r["gold_status"], []).append(
            f'{r["patient_id"]}({r["test_intent"]})'
        )
    labels = {
        "count": len(rows),
        "gold_distribution": dict(dist.most_common()),
        "by_class": {k: sorted(v) for k, v in intent_by_class.items()},
        "gate_rules_snapshot": {
            "surgery_allowlist": ["ACL_RECON"],
            "graft_allowlist": ["hamstring_autograft"],
            "concomitant_action": "manual_review_required",
            "nrs_red_flag_threshold": 6,
        },
        "notes": (
            "gold_status는 saferx-v2/scripts/extract_redact.py의 현행 게이트 규칙을 "
            "그대로 옮긴 결정론적 함수로 계산됨. 규칙이 바뀌면 이 파일을 재생성해야 함. "
            "'ready_for_reporter'는 게이트 통과를 뜻하며, 실제 파이프라인은 데이터 부족 "
            "시 insufficient_evidence로 정직하게 강등할 수 있음 (P001/P003 사례)."
        ),
    }
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)

    print(f"wrote {dataset_path} ({len(rows)} rows)")
    print(f"wrote {labels_path}")
    print()
    print("gold 분포:")
    for k, v in dist.most_common():
        print(f"  {k:<25} {v:>3}명")


if __name__ == "__main__":
    main()
