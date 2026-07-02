export type SurgeryType = "ACL_RECON" | "ROTATOR_CUFF" | "TKA";

export type LoadLevel = "none" | "light" | "moderate" | "full";

export const LOAD_LABEL: Record<LoadLevel, string> = {
  none: "무하중",
  light: "경하중",
  moderate: "중등도 하중",
  full: "전체중 부하",
};

export const LOAD_ORDER: LoadLevel[] = ["none", "light", "moderate", "full"];

export const SURGERY_LABEL: Record<SurgeryType, string> = {
  ACL_RECON: "전방십자인대(ACL) 재건술",
  ROTATOR_CUFF: "회전근개 봉합술",
  TKA: "인공관절 치환술(TKA)",
};

export interface PatientInput {
  surgeryType: SurgeryType;
  recoveryWeek: number;
  age: number;
  graftType: string;
  notes: string;
}

export interface ExerciseSpec {
  id: string;
  name: string;
  description: string;
  romMin: number;
  romMax: number;
  loadLevel: LoadLevel;
  movementTag: string;
}

export interface PrescriptionItem extends ExerciseSpec {
  setsReps: string;
}

export interface StageRule {
  id: string;
  surgeryType: SurgeryType;
  stageLabel: string;
  weekMin: number;
  weekMax: number;
  romLimit: [number, number];
  loadLimit: LoadLevel;
  forbiddenMovementTags: string[];
  requiredMovementTags: string[];
  source: string;
}

export type ViolationType =
  | "ROM_EXCEEDED"
  | "LOAD_EXCEEDED"
  | "FORBIDDEN_MOVEMENT"
  | "MISSING_REQUIRED_ITEM";

export interface ValidationIssue {
  itemId: string;
  itemName: string;
  ruleId: string;
  type: ViolationType;
  detail: string;
}

export interface CorrectionLogEntry {
  itemId: string;
  itemName: string;
  ruleId: string;
  before: string;
  after: string;
  reason: string;
}

export type AgentKey =
  | "orchestrator"
  | "generator"
  | "validator"
  | "corrector"
  | "reporter";

export interface AttemptRecord {
  attempt: number;
  prescription: PrescriptionItem[];
  issues: ValidationIssue[];
  corrections: CorrectionLogEntry[];
}

export interface PipelineResult {
  input: PatientInput;
  rule: StageRule;
  attempts: AttemptRecord[];
  finalPrescription: PrescriptionItem[];
  finalIssueCount: number;
  consistencyRuns: boolean[];
}
