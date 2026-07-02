export type SurgeryType = "ACL_RECON";

export const SURGERY_LABEL: Record<SurgeryType, string> = {
  ACL_RECON: "전방십자인대(ACL) 재건술",
};

export type GraftType = "hamstring_autograft" | "patellar_tendon_autograft" | "allograft";

export const GRAFT_LABEL: Record<GraftType, string> = {
  hamstring_autograft: "슬건 자가이식 (Hamstring Autograft)",
  patellar_tendon_autograft: "슬개건 자가이식 (Patellar Tendon Autograft)",
  allograft: "동종이식 (Allograft)",
};

export type WeightBearingStatus = "NWB" | "PWB" | "WBAT" | "FWB";

export const WEIGHT_BEARING_LABEL: Record<WeightBearingStatus, string> = {
  NWB: "무하중 (NWB)",
  PWB: "부분 체중부하 (PWB)",
  WBAT: "통증 허용 체중부하 (WBAT)",
  FWB: "전체중 부하 (FWB)",
};

export const WEIGHT_BEARING_ORDER: WeightBearingStatus[] = ["NWB", "PWB", "WBAT", "FWB"];

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

export interface PatientInput {
  surgeryType: SurgeryType;
  phase: RehabPhase;
  weekPostOp: number;
  age: number;
  graftType: GraftType;
  concomitantProcedure: string | null;
  painNrs: number | null;
  swelling: boolean;
  notes: string;
}

export interface ExerciseSpec {
  id: string;
  name: string;
  description: string;
  romMin: number;
  romMax: number;
  weightBearing: WeightBearingStatus;
  movementTag: string;
  source: string;
}

export interface PrescriptionItem extends ExerciseSpec {
  setsReps: string;
}

export type ViolationType =
  | "ROM_EXCEEDED"
  | "WEIGHT_BEARING_EXCEEDED"
  | "FORBIDDEN_MOVEMENT"
  | "MISSING_REQUIRED_ITEM"
  | "RED_FLAG";

export interface ValidationIssue {
  itemId: string;
  itemName: string;
  ruleId: string;
  type: ViolationType;
  detail: string;
  source: string;
}

export interface CorrectionLogEntry {
  itemId: string;
  itemName: string;
  ruleId: string;
  before: string;
  after: string;
  reason: string;
}

export type AgentKey = "extractor" | "rag" | "judge" | "corrector" | "generator" | "reporter";

export interface AttemptRecord {
  attempt: number;
  prescription: PrescriptionItem[];
  issues: ValidationIssue[];
  corrections: CorrectionLogEntry[];
}

export interface ManualReviewItem {
  itemName: string;
  reason: string;
}

// Reporter 에이전트 출력 포맷. 임상 문서에서 흔히 쓰는 SOAP 노트 구조를 그대로 채택.
export interface SoapNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface PipelineResult {
  input: PatientInput;
  attempts: AttemptRecord[];
  finalPrescription: PrescriptionItem[];
  finalIssueCount: number;
  manualReviewRequired: boolean;
  manualReviewItems: ManualReviewItem[];
  insufficientEvidence: boolean;
  protocolSource: string;
  consistencyRuns: boolean[];
  soapNote: SoapNote;
}

export class UnsupportedSurgeryError extends Error {}
