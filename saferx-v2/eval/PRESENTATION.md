# SafeRx — ACL 재활 처방 파이프라인 실험 요약
_2페이지 발표 자료 · Upstage Hackathon 2026_

---

## Page 1

### 문제 정의
**ACL 재건술 환자에게 LLM으로 재활 운동을 처방해도 안전한가?**  
그냥 맡기면 **처방 25%가 임상 위험**. 우리는 결정론 안전 게이트 + LLM 서술 + 독립 심사의 3계층 위계로 해결.

### 스코프
- **대상 수술**: ACL 재건술 (hamstring autograft)만
- **평가 페르소나**: 9명 (`saferx-v2/eval/dataset_acl.jsonl`)
- **핵심 규칙 셋**: 22개 안전 규칙, 30개 운동 라이브러리

### 3가지 아키텍처 비교
| # | 이름 | 구성 | LLM 콜/성공 |
|---|---|---|---:|
| A | **Multi-agent** (현행) | 결정론 6단 + reporter LLM + judge LLM | 2 |
| B | **Single-agent** (baseline) | LLM 하나가 게이트+처방 전부 | 1 |
| C | **Combined** (제안) | 결정론 6단 + reporter·judge 1콜 병합 | **1** |

### 결과 ① — Status 분류 F1 (ACL 9명)
| 지표 | A. Multi | B. Single | C. Combined |
|---|---:|---:|---:|
| Accuracy | 0.778 | **1.000** | 0.778 |
| Macro F1 | 0.929 | **1.000** | 0.929 |
| Weighted F1 | 0.873 | **1.000** | 0.873 |

> **"Single 만점?"** — 발표의 반전이 여기서 시작.

### 결과 ② — 실질 안전 감사 (승인된 처방 재검증)
| 지표 | A. Multi | B. Single | C. Combined |
|---|---:|---:|---:|
| 처방 발행 | 6 | 8 | 6 |
| 라이브러리 밖 운동 (hallucination) | 0 | 0 | 0 |
| **Hard 안전 규칙 위반 쌍** | **0** | **4** | **0** |
| **완전 통과 처방 비율** | **100%** | **75%** | **100%** |

**Single이 놓친 케이스**: P001(붓기+PHASE_I) 에 Ankle pump/Clamshell 처방, P003(붓기+PHASE_I) 에 Ankle pump/Heel slide 처방 → **REDFLAG-01 위반**(붓기 환자에게 dynamic 운동 금지).

**Multi/Combined는 이 두 케이스를 `insufficient_evidence`로 정직하게 거부** → F1은 낮지만 안전 판단은 옳음.

---

## Page 2

### 결과 ③ — 편향 실험 (인공 오류 주입 18케이스)
정상 리포트에 3종 오류를 인위 주입 → 두 심사 아키텍처의 검출률 비교:

| 오류 종류 | Multi (독립 심사) | Combined (자기 심사) |
|---|---:|---:|
| HALLU (처방에 없는 운동 추가) | 0/6 (0%) | 0/6 (0%) |
| DOSAGE (용량 변조) | 0/6 (0%) | 0/6 (0%) |
| DIAG (진단어 삽입) | 6/6 (100%) | 6/6 (100%) |
| **전체 검출률** | **33%** | **33%** |

**두 심사자 완전 동률** — actor/critic 분리의 실측 이득 없음.

---

### 🎯 30초 스토리 — 우리가 효율적인 이유

> **"안전 유지 + 비용 반토막"**
>
> - Multi(현행)는 Macro F1 0.929, 처방 안전 위반 0건, LLM 콜 **2회**
> - **Combined(제안)는 F1·안전 성능이 정확히 동일하면서 LLM 콜 1회**
> - 편향 검출률도 동률 → 심사자 분리의 실측 이득 없음
> - 결정론 파이프라인이 안전의 90%를 담당하므로 LLM 심사는 합쳐도 잃는 게 없음
>
> **환경변수 하나(`SAFERX_JUDGE_MODE=split|combined`)로 즉시 전환**. 데모/저비용엔 Combined, 규제 대응엔 Multi를 병렬 지원하는 유일한 아키텍처.

---

### 핵심 인사이트 3가지
1. **Headline F1의 함정** — Single이 만점이지만 처방 25%가 임상 위험. 지표만 보면 잘못된 아키텍처를 뽑음.
2. **진짜 안전 계층은 결정론 코드** — LLM 심사자 분리보다 결정론 게이트가 90% 담당. Multi vs Combined 차이가 F1·검출률에서 0이 나오는 이유.
3. **위계로 얻은 유연성** — orchestrator(지휘) / reporter·judge(전문 권한) / 5 executor(실행) 3계층 덕분에 심사 모드를 코드 수정 없이 토글 가능.

### 배포 시나리오별 권장
| 상황 | 추천 | 이유 |
|---|---|---|
| 데모·저비용 | **Combined** | 안전 유지, 비용 반토막 |
| 임상·규제 | **Multi** | 위계 감사·모델 교체 옵션 |
| 결정론 삭제? | **금지** | 25% unsafe로 실증됨 |

### 정직한 한계
- ACL 9명 · 실질 유효 표본 작음 → 통계적 확실성 낮음
- NRS≥6 페르소나 부재 → 새 red_flag 규칙은 별도 4건으로만 확인
- PHASE_I 라이브러리 공백으로 P001·P003이 `insufficient_evidence` (안전 판단은 옳음, 다음 라이브러리 보강 필요)

### 재현
```bash
python3 saferx-v2/scripts/eval_f1.py --mode multi  --acl-only   # 0.929 macro F1, 0 위반
python3 saferx-v2/scripts/eval_f1.py --mode single --acl-only   # 1.000 F1, 4 위반
python3 saferx-v2/scripts/eval_judge_mode.py                    # Multi vs Combined
python3 saferx-v2/scripts/eval_injection_bias.py                # 편향 시연
```

**저장소**: https://github.com/1jaekim/UPSTAGE_Hackathon (dev 브랜치)  
- 파이프라인: `saferx-v2/scripts/`
- 평가 데이터셋: `saferx-v2/eval/dataset_acl.jsonl`
- 실험 결과 JSON: `saferx-v2/eval/results/`
