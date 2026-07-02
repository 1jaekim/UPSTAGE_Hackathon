# spec.md — SafeRx Harness: Post-Op Exercise Therapy SOAP Report Agent

> Six elements of outcome clarification. This document is the source of truth for the feature.
> Every skill/agent must not violate this spec; on conflict, the spec wins.
> The input contract is anchored to the **trigger input schema** sent by the frontend (`src/api/harness.ts`).
> ※ SOAP = Subjective · Objective · Assessment · Plan.
>
> **Section order (required):** 1. 목표(Goal) · 2. 맥락(Context) · 3. 범위(Scope) · 4. 제약(Constraints) · 5. 출력 형식(Output) · 6. 성공기준(Success Criteria)

---

## 1. 목표 (Goal / Purpose)

Build a clinical-support agent that proposes **five recommended exercises as a SOAP-structured review report**,
grounded in our own data, to physical therapists managing post-op rehabilitation.

The report is not a bare prescription — it also provides the rationale ("why this exercise") to support the
PT's judgment and carry educational value. The final clinical decision is made by the human PT; the agent only
proposes with evidence (proposal + rationale, never a directive).

---

## 2. 맥락 (Context)

Post-op exercise therapy is growing in clinical importance, and more therapists are moving from manual therapy
to exercise therapy. Many of them are **junior physical therapists**, so a report that explains *why* each
exercise is chosen lowers the barrier and builds their clinical reasoning.

Because this is a clinical, safety-sensitive domain, the agent must never invent exercises or claims outside
our own data, and every safety verdict must be deterministic and reproducible rather than left to LLM
judgment. The human PT remains the decision-maker; the agent is an evidence-backed proposer.

---

## 3. 범위 (Scope)

- Answers are generated **only from our own data** (the ChromaDB guideline documents and the
  `data/rule_table.json` rule table). No general claims or invented exercises unsupported by that data.
- Covered surgery: `surgery == "ACL_RECON"` (knee) only. Any other value ends immediately as
  `unsupported_surgery`.
- The report contains **exactly five recommended exercises** (Plan section).

### 3-1. Out of scope (explicit exclusions)
- Measured criterion-based items (e.g., quadriceps strength) are not auto-judged and are flagged as
  "PT manual review required."
- Cases with `concomitant_procedure != null` use a wholly different rule set and are out of scope for this
  version → escalated to manual review (§4-E).
- No diagnosis or definitive directives (proposal + rationale only). The final decision belongs to the PT.

### 3-2. Input contract (what the agent accepts)
The frontend sends fields **already structured** via dropdowns, checkboxes, and numeric inputs. Therefore
`input-parser` does not re-parse structured fields back into natural language — it **passes them through** —
and the only free-text field is `notes`.

#### Trigger input schema (draft-07, canonical)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SafeRxHarnessTriggerInput",
  "type": "object",
  "required": ["surgery", "week_post_op", "age", "swelling", "notes", "surgery_details"],
  "additionalProperties": false,
  "properties": {
    "surgery": { "type": "string", "enum": ["ACL_RECON"] },
    "week_post_op": { "type": "integer", "minimum": 0 },
    "age": { "type": "integer", "minimum": 1 },
    "concomitant_procedure": { "type": ["string", "null"] },
    "pain_nrs": { "type": ["integer", "null"], "minimum": 0, "maximum": 10 },
    "swelling": { "type": "boolean" },
    "notes": { "type": "string" },
    "surgery_details": {
      "type": "object",
      "required": ["phase", "graft_type"],
      "properties": {
        "phase": { "type": "string", "enum": ["PHASE_I","PHASE_II","PHASE_III","PHASE_IV","PHASE_V"] },
        "graft_type": { "type": "string", "enum": ["hamstring_autograft"] }
      }
    }
  }
}
```

#### Field consumers (who actually uses each field for judgment)
| Field | Structured | Consuming skill / use |
|---|---|---|
| `surgery` | ✅ | `scope-gate` immediate support check; branch key for all downstream skills |
| `week_post_op` | ✅ | `exercise-retriever` search filter; `safety-validator` phase-lookup key |
| `surgery_details.phase` | ✅ | `exercise-retriever` filter; `safety-validator` per-phase rule-lookup key |
| `surgery_details.graft_type` | ✅ | `exercise-retriever` / `safety-validator` graft-specific rule branch |
| `pain_nrs` | ✅ | `safety-validator` red-flag check (§4-D) |
| `swelling` | ✅ | `safety-validator` red-flag check (§4-D) |
| `concomitant_procedure` | ✅ | `scope-gate` — if present, escalate to manual review (§4-E) |
| `age` | ✅ | Not used in rule judgment. `report-writer` records it in SOAP Subjective only |
| `notes` | ❌ (free text) | Skimmed by `input-parser` for reference only. Not re-structured into downstream judgment (§4-B/C); redaction target (§4-F) |

Note: the trigger payload contains **no direct identifiers** (no name, contact, or chart number — absent by
schema). The practical privacy surface is therefore just the `notes` free text and the exact `age` value.
`record_id` (a correlation key) is **assigned internally by the harness**, not sent by the frontend.

---

## 4. 제약 (Constraints / Non-functional Requirements)

- **§4-A Data-bound generation**: No generation from knowledge outside our data. On insufficient coverage,
  return `insufficient_evidence` and do not fill in arbitrary exercises.
- **§4-B input-parser pass-through**: Already-structured fields (surgery/pain_nrs/swelling/phase/graft_type,
  etc.) are not re-parsed from text — pass them through as-is.
- **§4-C notes non-determinism guard**: `notes` is skimmed for reference only; do not structure new fields
  from it and feed them into downstream judgment (keep same input → same verdict).
- **§4-D red flag**: If `pain_nrs` exceeds threshold or `swelling == true`, dynamic exercises auto-fail →
  `correction-planner` force-substitutes all with isometric exercises.
- **§4-E concomitant procedure**: If `concomitant_procedure != null`, `scope-gate` escalates immediately with
  `manual_review_required: true, reason: "concomitant_procedure"`, and `safety-validator` does not evaluate
  the case.
- **§4-F privacy**: Redact `notes` before sending to the LLM (mask national ID, phone, name, institution).
  Prefer generalizing `age` to an age band over the exact value. Use `record_id` as an internal correlation
  key only. Health data is sensitive; third-party LLM use requires review of no-retention, processing
  delegation, and cross-border transfer (production roadmap; legal/DPO review).
- **§4-G week/phase consistency**: If `week_post_op` and `surgery_details.phase` conflict (e.g., week 2 ↔
  PHASE_IV), **conservatively adopt the lower phase** and add a `phase_week_mismatch` flag to the report.
  ※ Team decision required.
- **§4-H language / length**: SOAP narratives, exercise names, and rationale are bilingual (Korean/English).
  Within one A4 page; the Plan is limited to five exercises.
- **§4-I role limits**: No diagnosis or definitive directives. Proposal + rationale only; the final decision
  is the physical therapist's. Include a rationale for every exercise.

---

## 5. 출력 형식 (Output)

**Format: a single JSON file.** It carries the four SOAP sections; narrative fields are **bilingual
(Korean + English)**. Total length is **within one A4 page** when rendered. SOAP narratives stay concise; the
Plan contains **exactly five exercises**.

### Output schema
```json
{
  "report_meta": {
    "record_id": "rec_0007",
    "surgery": "ACL_RECON",
    "week_post_op": 2,
    "phase": "PHASE_I",
    "graft_type": "hamstring_autograft",
    "format": "SOAP",
    "language": "ko-en",
    "protocol_source": { "name": "...", "url": "..." },
    "generated_at": "2026-07-02T00:00:00Z"
  },
  "soap": {
    "subjective": { "ko": "나이·주호소 등 환자 보고", "en": "Age, chief complaint, patient-reported" },
    "objective":  { "ko": "주차·단계·부종·통증·이식건 등 관찰치", "en": "Week, phase, swelling, pain, graft" },
    "assessment": { "ko": "재활 단계 판단·주의·red flag 여부", "en": "Rehab phase, precautions, red-flag status" },
    "plan": {
      "ko": "이번 단계 운동 계획 요약",
      "en": "Exercise plan summary for this phase",
      "exercises": [
        {
          "name": { "ko": "대퇴사두근 등척성 수축", "en": "Quadriceps isometric set" },
          "sets": 3, "reps": 10,
          "frequency": { "ko": "1일 3회", "en": "3x daily" },
          "intensity": { "ko": "통증 없는 최대 수축", "en": "Pain-free maximal contraction" },
          "rationale": { "ko": "초기 근활성·근위축 방지, 이식건 부하 낮음", "en": "Early activation, low graft load" },
          "source": "protocol document id/name",
          "safety_checked": true
        }
      ]
    }
  },
  "manual_review": [
    { "item": "quadriceps_strength_criterion", "note": { "ko": "PT 수동 확인 필요", "en": "PT manual review required" } }
  ],
  "safety": { "final_gate_passed": true, "violations": [] }
}
```
`exercises` must be **exactly five**. Each exercise must include sets, reps, frequency, intensity, rationale,
and source, and must be `safety_checked: true` (passed the deterministic safety gate).

Excluded from the report: narratives unsupported by our data, exercises that failed the safety gate, and any
item without a source. If `unsupported_surgery == true`, output only an "unsupported surgery type" notice
instead of a prescription/report, and stop.

---

## 6. 성공기준 (Success Criteria)

Validation runs as an **ordered sequence of gates**. Each gate is a hard precondition for the next: the
deterministic protocol check runs **first**, and the **Judge LLM is invoked only if that check passes**. A
report succeeds only if it clears all gates in order.

### 6-1. Gate 1 — Deterministic protocol check (runs first)
- `safety-validator` compares every exercise against `data/rule_table.json` and confirms
  `safety.violations == []` and every exercise `safety_checked == true`.
- This is the authoritative safety verdict; it is code-deterministic, not LLM judgment.
- **If violations exist → the Judge LLM is not invoked.** The flow enters the correction loop
  (`correction-planner` → re-search → re-validate, bounded retries); if violations remain, escalate to
  `manual_review_required`.

### 6-2. Gate 2 — Judge LLM verdict (runs only after Gate 1 passes) — structured binary rubric
| # | Check | Pass condition |
|---|---|---|
| J1 | SOAP completeness | All four S·O·A·P sections present and non-empty (both ko and en) |
| J2 | Exercise count | `plan.exercises` is exactly five |
| J3 | Exercise field completeness | Each exercise has sets, reps, frequency, intensity, rationale, source |
| J4 | Groundedness | Each exercise cites a source from our data; no unsourced narrative |
| J5 | Bilingual | Required narrative fields contain both Korean and English |
| J6 | Length | Within one A4 page (length budget) |

- The Judge LLM does **not** re-decide safety (that was settled in Gate 1); it confirms the Gate-1 result and
  judges only report structure/quality/groundedness.
- If any of J1–J6 fails → regenerate or escalate to manual review.

### 6-3. Gate 3 — JSON artifact validation (format)
- JSON parses successfully (syntactically valid) — a precondition for evaluating Gates 1–2.
- Conforms to the §5 output schema (required keys, types, five-exercise constraint).

### Reproducibility (invariant)
- The reproducibility guarantee covers the safety verdict (Gate 1), the adopted exercise list, and schema
  conformance. LLM prose (SOAP narratives) is not guaranteed byte-identical.

---

## Appendix — Skill pipeline (workflow.md)
```
input → input-parser → scope-gate → exercise-retriever → safety-validator (protocol check)
  → (fail) correction-planner → exercise-retriever (re-search) → safety-validator (re-check)
  → prescription-writer → safety-validator (completeness check) → report-writer
  → judge-llm (report acceptance, Gate 2 — runs only if protocol check passed) → web output
```
Ordering: the deterministic protocol check (Gate 1, `safety-validator`) always runs first and is the hard
precondition; the Judge LLM (Gate 2) is invoked only after it passes. The correction path is a loop within
this single pipeline, not a separate variant — on a safety failure the flow re-searches and re-validates until
it passes (bounded retries) and returns the result.
