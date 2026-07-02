# SafeRx 평가 데이터셋

`saferx-v2/` 파이프라인의 성능 실험에 사용한 30개 페르소나 테스트 셋과 정답, 그리고 각 실험 결과를 자립형(self-contained) 아티팩트로 모아둔 폴더.

## 파일

| 파일 | 내용 |
|---|---|
| `dataset.jsonl` | 30줄, 한 줄이 하나의 테스트 케이스 (input + gold label + intent 메타) |
| `gold_labels.json` | {PID → gold_status} 요약 + 클래스 분포 + 게이트 스냅샷 |
| `build_dataset.py` | 위 두 파일을 원본 `samples/personas/`에서 재생성하는 결정론 스크립트 |
| `results/*.json` | 각 아키텍처 실험의 실측 지표 |

## 원본 데이터

- **페르소나 30명**: `saferx-v2/samples/personas/P001~P030.json`
- **원본 CSV**: `saferx-v2/data/patients_soap_30.csv` (팀이 만든 SOAP 페르소나 원본)
- **변환 스크립트**: `saferx-v2/scripts/convert_personas.py`
- **원본 사람 라벨**: `saferx-v2/samples/personas/_index.json`의 `expected_status`

## Gold 라벨 계산 방식

`dataset.jsonl`의 `gold_status`는 사람 라벨을 그대로 쓰지 않고, 현행 `extract_redact.py`의 게이트 순서를 결정론적으로 옮긴 함수로 재계산한다:

```
1. surgery != "ACL_RECON"                → unsupported_surgery
2. graft_type != "hamstring_autograft"   → unsupported_case
3. concomitant_procedure != null         → manual_review_required
4. pain_nrs >= 6                          → red_flag
5. else                                   → ready_for_reporter
```

**규칙이 바뀌면 `build_dataset.py`를 재실행해서 gold을 새로 잡아야 한다.** `original_expected_status` 필드에 사람 라벨이 그대로 보존되어 있어 diff 비교 가능.

## 클래스 분포 (30명)

| gold_status | count | 페르소나 |
|---|---:|---|
| unsupported_surgery | 21 | 비-ACL 수술 (THA/RCR/ACH) |
| ready_for_reporter | 8 | P001~P008 (ACL + hamstring + no concomitant + NRS<6) |
| manual_review_required | 1 | P009 (concomitant=meniscal_repair) |
| red_flag | 0 | 이 셋엔 NRS>=6 페르소나 없음 |

**정직한 한계**: 30명 중 22명은 게이트 규칙만으로 결정되는 tautology 케이스(파이프라인이 자기 규칙으로 자기를 채점). 진짜 파이프라인 성능은 나머지 **8명**에서만 관측됨.

## 실험 결과 (`results/`)

| 파일 | 실험 | 요약 |
|---|---|---|
| `multi_agent.json` | 현행 파이프라인 (결정론 + reporter LLM + judge LLM) | Accuracy 0.933, Macro F1 0.952 |
| `single_agent.json` | LLM 하나가 게이트+처방 전부 | Accuracy 1.000이지만 처방의 25%가 안전 위반 |
| `judge_mode_combined.json` | reporter+judge를 한 LLM 콜로 병합 | F1 동일, LLM 호출 반토막 |
| `injection_bias.json` | 6명 × 3종 인공 오류 주입 (18케이스) | 두 심사자 검출률 동률 (33%) |

## 재현 방법

```bash
# 1. dataset 재생성 (규칙 변경 시)
python3 saferx-v2/eval/build_dataset.py

# 2. 각 실험 재실행
python3 saferx-v2/scripts/eval_f1.py --mode multi
python3 saferx-v2/scripts/eval_f1.py --mode single
python3 saferx-v2/scripts/eval_judge_mode.py
python3 saferx-v2/scripts/eval_injection_bias.py
```

## 알려진 편차

| PID | gold | pipeline 실측 | 원인 |
|---|---|---|---|
| P001 | ready_for_reporter | insufficient_evidence | PHASE_I 등척성 라이브러리 3개 미만 |
| P003 | ready_for_reporter | insufficient_evidence | 위와 동일 |

두 오분류는 파이프라인 결함이 아니라 exercise library의 PHASE_I 데이터 공백 때문. 라이브러리 보강 후 재평가 필요.
