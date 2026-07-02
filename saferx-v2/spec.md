# spec.md — SafeRx: Post-Op ACL Exercise Therapy SOAP Report Agent

> This document is the source of truth. Every skill / agent / script must not violate it; on conflict, the spec wins.
> Implementation decisions for anything this spec leaves open are recorded in `DECISIONS.md`.

---

## 목표
> 무엇을 만드는가? 한 문장으로 작성하세요.

Automatically generate a SOAP-structured review report (a single JSON file) that proposes exactly five evidence-backed recommended exercises — grounded only in our own data — for physical therapists managing post-op ACL reconstruction (hamstring autograft) rehabilitation.

---

## 맥락
> 왜 이 작업이 필요한가? 대상과 사용 목적을 적으세요.

대상 (Target users): Physical therapists managing post-op exercise therapy — especially **junior PTs** who benefit from seeing *why* each exercise was chosen.

사용 목적 (Purpose): Post-op exercise therapy is growing in clinical importance. A report that pairs each exercise with its rationale lowers the entry barrier and builds clinical reasoning. Because this is a safety-sensitive clinical domain, every safety verdict must be **deterministic and reproducible (code, not LLM judgment)**, and the agent must never invent exercises outside our data. The human PT remains the final decision-maker; the agent only proposes with evidence.

---

## 범위
> 어디까지 포함/제외 하는가?

포함 (In scope):
- Surgery `ACL_RECON` (knee) with `graft_type == "hamstring_autograft"` only.
- Answers generated **only from our own data**: the exercise/guideline documents (`data/exercise_library.json`, ChromaDB in production) and the 22-rule table (`data/rule_table.json`).
- Structured trigger input from the frontend (dropdowns / checkboxes / numbers); the only free-text field is `notes`. Canonical input schema (draft-07): required `surgery, week_post_op, age, swelling, notes, surgery_details{phase, graft_type}`; optional `concomitant_procedure, pain_nrs(0–10)`. No direct identifiers are sent; `record_id` is assigned internally by the harness.

제외 (Out of scope):
- Any other surgery type → end immediately as `unsupported_surgery`.
- `concomitant_procedure != null` → uses a different rule set; escalate to manual review.
- Measured criterion-based items (e.g., quadriceps strength) → not auto-judged; flagged "PT manual review required."
- Diagnosis or definitive directives — proposal + rationale only.

---

## 제약
> 반드시 지켜야 할 조건은 무엇인가? (형식, 언어, 분량, 시간 등)

- **[4-A] Data-bound**: never generate from knowledge outside our data; on insufficient coverage return `insufficient_evidence` instead of filling in exercises.
- **[4-B] Pass-through**: already-structured fields are never re-parsed from text.
- **[4-C] Notes guard**: `notes` is reference-only; never structure new judgment fields from it (same input → same verdict).
- **[4-D] Red flag**: `pain_nrs ≥ 7` or `swelling == true` → dynamic exercises auto-fail; the correction step force-substitutes all with isometric exercises.
- **[4-E] Concomitant procedure**: if present, escalate `manual_review_required` immediately; the safety gate does not evaluate the case.
- **[4-F] Privacy**: redact `notes` **in code, before any LLM contact** (mask national ID / phone / name / institution); generalize `age` to a band; raw notes and exact age never reach an LLM. Third-party LLM use requires legal/DPO review (retention, delegation, cross-border transfer).
- **[4-G] Week/phase consistency**: on conflict, conservatively adopt the **lower** phase and flag `phase_week_mismatch` (mapping: `data/week_phase_map.json`, provisional).
- **[4-H] Language / length**: all narratives bilingual (Korean + English); within one A4 page (proxy: ≤ 3,500 narrative characters).
- **[4-I] Role limit**: no diagnosis, no directives; every exercise carries a rationale; the PT makes the final decision.

---

## 출력 형식
> 어떤 형태로 결과가 나와야 하는가?

파일명 (File): `work/50_report.json` — a single JSON file.

섹션 순서 (Section order): `report_meta` → `soap.subjective` → `soap.objective` → `soap.assessment` → `soap.plan` (with `exercises`) → `manual_review` → `safety`.

분량 (Length): within one A4 page when rendered; `plan.exercises` contains **exactly five** items, each with `name(ko/en), sets, reps, frequency, intensity, rationale, source, safety_checked: true`.

Excluded from the report: narratives unsupported by our data, exercises that failed the safety gate, and any item without a source. If the surgery is unsupported, output only an "unsupported surgery type" notice and stop.

---

## 성공 기준
> ⚠️ 이 항목을 가장 먼저 작성하세요.
> "예/아니오"로 판단 가능한 형태로 작성합니다.
> Gates run in order; each is a hard precondition for the next. The deterministic check (Gate 1) always runs first; the LLM judge (Gate 2) is invoked only if Gate 1 passed.

**Gate 1 — Deterministic protocol check (code, authoritative):**
- [ ] Every exercise was compared against `data/rule_table.json` and `safety.violations == []`.
- [ ] Every prescribed exercise has `safety_checked == true` (hard-violation count 0; 1–10 → bounded correction loop, ≥ 11 or > 5 iterations → escalate manual review).
- [ ] The completeness re-check passed on the final five (no missing sets/reps/frequency/source; no dosage exceeding the library — DOS-02).

**Gate 2 — LLM judge (structure/quality only; never re-decides safety):**
- [ ] J1: all four S·O·A·P narratives are substantive, consistent with the context, and use proposal + rationale framing (ko AND en).
- [ ] J4: every claim traces to pipeline data; no invented exercise, parameter, or clinical statement.

**Gate 3 — Artifact validation (code):**
- [ ] The output parses as valid JSON and conforms to the output schema above.
- [ ] `plan.exercises` is exactly five; required fields present; bilingual fields non-empty; narrative length ≤ 3,500 chars.

**Reproducibility (invariant):**
- [ ] Same input → byte-identical safety verdict, adopted exercise list, and schema conformance (LLM prose may vary).
