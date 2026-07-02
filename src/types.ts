export type SurgeryType = "ACL_RECON";

export const SURGERY_LABEL: Record<SurgeryType, string> = {
  ACL_RECON: "전방십자인대(ACL) 재건술",
};

// ChromaDB에 있는 knee 프로토콜 문서가 슬건 자가이식 ACL 재건만 다루므로 이 값 하나로 고정.
// 다른 이식건(슬개건 자가이식/동종이식) 프로토콜 문서가 추가되면 그때 확장.
export type GraftType = "hamstring_autograft";

export const GRAFT_LABEL: Record<GraftType, string> = {
  hamstring_autograft: "슬건 자가이식 (Hamstring Autograft)",
};

// ChromaDB에 적재된 knee(ACL) 프로토콜 문서의 단계 구분(Phase I~V)과 맞춘 값.
export type RehabPhase = "PHASE_I" | "PHASE_II" | "PHASE_III" | "PHASE_IV" | "PHASE_V";

export const REHAB_PHASE_LABEL: Record<RehabPhase, string> = {
  PHASE_I: "Phase I — 즉시 수술 후",
  PHASE_II: "Phase II",
  PHASE_III: "Phase III",
  PHASE_IV: "Phase IV",
  PHASE_V: "Phase V — 복귀 단계",
};

export const REHAB_PHASE_ORDER: RehabPhase[] = ["PHASE_I", "PHASE_II", "PHASE_III", "PHASE_IV", "PHASE_V"];

// 수술마다 모양이 달라지는 필드는 여기 안에 넣는다(트리거 스키마의 surgery_details와 대응).
// 다른 수술이 추가되면 `AclSurgeryDetails | RotatorCuffSurgeryDetails | ...` 식으로 유니온을 늘린다.
export interface AclSurgeryDetails {
  phase: RehabPhase;
  graftType: GraftType;
}

export type SurgeryDetails = AclSurgeryDetails;

export interface PatientInput {
  surgeryType: SurgeryType;
  weekPostOp: number;
  age: number;
  concomitantProcedure: string | null;
  painNrs: number | null;
  swelling: boolean;
  notes: string;
  surgeryDetails: SurgeryDetails;
}

// ---- 백엔드(rag/harness) 출력 계약. spec.md §5 출력 스키마 그대로 반영 ----

export interface Bilingual {
  ko: string;
  en: string;
}

export interface ReportExercise {
  name: Bilingual;
  sets: number;
  reps: number;
  intensity: Bilingual;
  rationale: Bilingual;
  source: string;
  safetyChecked: boolean;
}

export interface ProtocolSource {
  name: string;
  url: string | null;
  refs: string[];
}

export interface ReportMeta {
  recordId: string;
  surgery: SurgeryType;
  weekPostOp: number;
  phase: RehabPhase;
  graftType: GraftType;
  format: string;
  language: string;
  protocolSource: ProtocolSource;
  generatedAt: string;
}

export interface ManualReviewItem {
  item: string;
  note: Bilingual;
}

export interface SoapPlan extends Bilingual {
  exercises: ReportExercise[];
}

export interface Soap {
  subjective: Bilingual;
  objective: Bilingual;
  assessment: Bilingual;
  plan: SoapPlan;
}

export interface SafetyVerdict {
  finalGatePassed: boolean;
  violations: unknown[];
}

export interface HarnessReport {
  reportMeta: ReportMeta;
  soap: Soap;
  manualReview: ManualReviewItem[];
  safety: SafetyVerdict;
}

export type PipelineStatus =
  | "ready_for_reporter"
  | "unsupported_surgery"
  | "manual_review_required"
  | "insufficient_evidence"
  | "failed";

export const PIPELINE_STATUS_LABEL: Record<PipelineStatus, string> = {
  ready_for_reporter: "완료",
  unsupported_surgery: "지원하지 않는 수술 유형",
  manual_review_required: "PT 수동 검토 필요",
  insufficient_evidence: "근거 부족",
  failed: "처리 실패",
};

export interface PipelineResult {
  status: PipelineStatus;
  detail: string;
  report: HarnessReport | null;
  correctionUsed: boolean;
  iterations: number;
}
