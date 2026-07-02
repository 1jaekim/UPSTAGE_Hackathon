export interface PatientData {
  surgery: string;
  week: string;
  age: string;
  graftType: string;
  notes: string;
}

export interface AnimatedStep {
  agent: AgentKey;
  label: string;
  attempt?: number;
}

export type AgentKey = "orchestrator" | "generator" | "validator" | "corrector" | "reporter";
