// rag/hooks_server.py의 POST /run-harness를 호출하는 클라이언트.
// 엔드포인트는 .env(VITE_HARNESS_ENDPOINT)에 넣는다 (로컬 개발 시 http://127.0.0.1:8787/run-harness).
//
// 요청 바디 (수술 공통 필드는 최상위, 수술별 필드는 surgery_details에 중첩):
// {
//   "surgery": "ACL_RECON", "week_post_op": 2, "age": 45,
//   "concomitant_procedure": null, "pain_nrs": null, "swelling": false, "notes": "...",
//   "surgery_details": { "phase": "PHASE_I", "graft_type": "hamstring_autograft" }
// }
//
// 응답 바디 (rag/harness_runner.py의 반환 계약, spec.md §5 출력 스키마 그대로):
// {
//   "status": "ready_for_reporter" | "unsupported_surgery" | "manual_review_required"
//             | "insufficient_evidence" | "failed",
//   "detail": "...", "correction_used": bool, "iterations": int,
//   "report": { "report_meta": {...}, "soap": {...}, "manual_review": [...], "safety": {...} } | null
// }

import type {
  Bilingual,
  HarnessReport,
  ManualReviewItem,
  PatientInput,
  PipelineResult,
  PipelineStatus,
  ProtocolSource,
  ReportExercise,
  ReportMeta,
  SafetyVerdict,
  Soap,
} from "../types";

interface WireReportExercise {
  name: Bilingual;
  sets: number;
  reps: number;
  frequency: Bilingual;
  intensity: Bilingual;
  rationale: Bilingual;
  source: string;
  safety_checked: boolean;
}

interface WireReportMeta {
  record_id: string;
  surgery: PatientInput["surgeryType"];
  week_post_op: number;
  phase: string;
  graft_type: string;
  format: string;
  language: string;
  protocol_source: ProtocolSource;
  generated_at: string;
}

interface WireSoap {
  subjective: Bilingual;
  objective: Bilingual;
  assessment: Bilingual;
  plan: Bilingual & { exercises: WireReportExercise[] };
}

interface WireManualReviewItem {
  item: string;
  note: Bilingual;
}

interface WireSafety {
  final_gate_passed: boolean;
  violations: unknown[];
}

interface WireReport {
  report_meta: WireReportMeta;
  soap: WireSoap;
  manual_review: WireManualReviewItem[];
  safety: WireSafety;
}

interface WireResponse {
  status: PipelineStatus;
  detail: string;
  correction_used: boolean;
  iterations: number;
  report: WireReport | null;
}

function toExercise(e: WireReportExercise): ReportExercise {
  return {
    name: e.name,
    sets: e.sets,
    reps: e.reps,
    frequency: e.frequency,
    intensity: e.intensity,
    rationale: e.rationale,
    source: e.source,
    safetyChecked: e.safety_checked,
  };
}

function toReportMeta(m: WireReportMeta): ReportMeta {
  return {
    recordId: m.record_id,
    surgery: m.surgery,
    weekPostOp: m.week_post_op,
    phase: m.phase as ReportMeta["phase"],
    graftType: m.graft_type as ReportMeta["graftType"],
    format: m.format,
    language: m.language,
    protocolSource: m.protocol_source,
    generatedAt: m.generated_at,
  };
}

function toSoap(s: WireSoap): Soap {
  return {
    subjective: s.subjective,
    objective: s.objective,
    assessment: s.assessment,
    plan: { ko: s.plan.ko, en: s.plan.en, exercises: s.plan.exercises.map(toExercise) },
  };
}

function toManualReview(items: WireManualReviewItem[]): ManualReviewItem[] {
  return items.map((i) => ({ item: i.item, note: i.note }));
}

function toSafety(s: WireSafety): SafetyVerdict {
  return { finalGatePassed: s.final_gate_passed, violations: s.violations };
}

function toReport(r: WireReport): HarnessReport {
  return {
    reportMeta: toReportMeta(r.report_meta),
    soap: toSoap(r.soap),
    manualReview: toManualReview(r.manual_review),
    safety: toSafety(r.safety),
  };
}

function toWireSurgeryDetails(input: PatientInput): Record<string, unknown> {
  const details = input.surgeryDetails;
  return { phase: details.phase, graft_type: details.graftType };
}

export async function runPipeline(input: PatientInput): Promise<PipelineResult> {
  const endpoint = import.meta.env.VITE_HARNESS_ENDPOINT;
  if (!endpoint) {
    throw new Error("VITE_HARNESS_ENDPOINT가 설정되지 않았습니다. .env에 하네스 서버 URL을 넣어주세요.");
  }

  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      surgery: input.surgeryType,
      week_post_op: input.weekPostOp,
      age: input.age,
      concomitant_procedure: input.concomitantProcedure,
      pain_nrs: input.painNrs,
      swelling: input.swelling,
      notes: input.notes,
      surgery_details: toWireSurgeryDetails(input),
    }),
  });

  if (!res.ok) {
    throw new Error(`Harness 호출 실패 (HTTP ${res.status})`);
  }

  const wire = (await res.json()) as WireResponse;

  return {
    status: wire.status,
    detail: wire.detail,
    correctionUsed: wire.correction_used,
    iterations: wire.iterations,
    report: wire.report ? toReport(wire.report) : null,
  };
}
