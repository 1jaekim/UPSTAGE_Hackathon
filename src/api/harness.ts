// Timely에 구축된 Harness 웹훅을 호출하는 클라이언트.
// 엔드포인트는 .env(VITE_HARNESS_ENDPOINT)에 Timely 웹훅 URL을 넣으면 된다.
//
// 기대하는 응답 계약 (harness_agent_spec 2.1~2.6, 5의 json 예시 기준. snake_case):
// {
//   "unsupported_surgery": false,
//   "attempts": [
//     {
//       "attempt": 1,
//       "prescription": [{ "id", "name", "description", "rom_min", "rom_max",
//                           "weight_bearing": "NWB"|"PWB"|"WBAT"|"FWB", "movement_tag",
//                           "sets_reps", "source" }],
//       "issues": [{ "item_id", "item_name", "rule_id", "type", "detail", "source" }],
//       "corrections": [{ "item_id", "item_name", "rule_id", "before", "after", "reason" }]
//     }
//   ],
//   "final_prescription": [...],
//   "final_issue_count": 0,
//   "manual_review_required": false,
//   "manual_review_items": [{ "item_name", "reason" }],
//   "insufficient_evidence": false,
//   "protocol_source": "Mass General Hospital ACL Rehabilitation Protocol (massgeneral.org)",
//   "consistency_runs": [true, true, true],
//   "soap_note": { "subjective": "...", "objective": "...", "assessment": "...", "plan": "..." }
// }

import type {
  AttemptRecord,
  CorrectionLogEntry,
  PatientInput,
  PipelineResult,
  PrescriptionItem,
  SoapNote,
  ValidationIssue,
  WeightBearingStatus,
} from "../types";
import { UnsupportedSurgeryError } from "../types";

interface WireExercise {
  id: string;
  name: string;
  description: string;
  rom_min: number;
  rom_max: number;
  weight_bearing: WeightBearingStatus;
  movement_tag: string;
  sets_reps: string;
  source: string;
}

interface WireIssue {
  item_id: string;
  item_name: string;
  rule_id: string;
  type: ValidationIssue["type"];
  detail: string;
  source: string;
}

interface WireCorrection {
  item_id: string;
  item_name: string;
  rule_id: string;
  before: string;
  after: string;
  reason: string;
}

interface WireAttempt {
  attempt: number;
  prescription: WireExercise[];
  issues: WireIssue[];
  corrections: WireCorrection[];
}

interface WireResponse {
  unsupported_surgery?: boolean;
  attempts: WireAttempt[];
  final_prescription: WireExercise[];
  final_issue_count: number;
  manual_review_required: boolean;
  manual_review_items: { item_name: string; reason: string }[];
  insufficient_evidence: boolean;
  protocol_source: string;
  consistency_runs: boolean[];
  soap_note: SoapNote;
}

function toPrescriptionItem(e: WireExercise): PrescriptionItem {
  return {
    id: e.id,
    name: e.name,
    description: e.description,
    romMin: e.rom_min,
    romMax: e.rom_max,
    weightBearing: e.weight_bearing,
    movementTag: e.movement_tag,
    setsReps: e.sets_reps,
    source: e.source,
  };
}

function toValidationIssue(i: WireIssue): ValidationIssue {
  return {
    itemId: i.item_id,
    itemName: i.item_name,
    ruleId: i.rule_id,
    type: i.type,
    detail: i.detail,
    source: i.source,
  };
}

function toCorrectionLogEntry(c: WireCorrection): CorrectionLogEntry {
  return {
    itemId: c.item_id,
    itemName: c.item_name,
    ruleId: c.rule_id,
    before: c.before,
    after: c.after,
    reason: c.reason,
  };
}

function toAttemptRecord(a: WireAttempt): AttemptRecord {
  return {
    attempt: a.attempt,
    prescription: a.prescription.map(toPrescriptionItem),
    issues: a.issues.map(toValidationIssue),
    corrections: a.corrections.map(toCorrectionLogEntry),
  };
}

function normalize(input: PatientInput, wire: WireResponse): PipelineResult {
  return {
    input,
    attempts: wire.attempts.map(toAttemptRecord),
    finalPrescription: wire.final_prescription.map(toPrescriptionItem),
    finalIssueCount: wire.final_issue_count,
    manualReviewRequired: wire.manual_review_required,
    manualReviewItems: wire.manual_review_items.map((m) => ({ itemName: m.item_name, reason: m.reason })),
    insufficientEvidence: wire.insufficient_evidence,
    protocolSource: wire.protocol_source,
    consistencyRuns: wire.consistency_runs,
    soapNote: wire.soap_note,
  };
}

export async function runPipeline(input: PatientInput): Promise<PipelineResult> {
  const endpoint = import.meta.env.VITE_HARNESS_ENDPOINT;
  if (!endpoint) {
    throw new Error(
      "VITE_HARNESS_ENDPOINT가 설정되지 않았습니다. .env에 Timely 웹훅 URL을 넣어주세요.",
    );
  }

  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      surgery: input.surgeryType,
      phase: input.phase,
      graft_type: input.graftType,
      week_post_op: input.weekPostOp,
      age: input.age,
      concomitant_procedure: input.concomitantProcedure,
      pain_nrs: input.painNrs,
      swelling: input.swelling,
      notes: input.notes,
    }),
  });

  if (!res.ok) {
    throw new Error(`Harness 호출 실패 (HTTP ${res.status})`);
  }

  const wire = (await res.json()) as WireResponse;

  if (wire.unsupported_surgery) {
    throw new UnsupportedSurgeryError("지원하지 않는 수술 유형입니다. 현재는 ACL 재건술만 지원합니다.");
  }

  return normalize(input, wire);
}
