import type { AgentKey } from "../types";

export const AGENT_ORDER: AgentKey[] = ["orchestrator", "generator", "validator", "corrector", "reporter"];

export const AGENT_META: Record<AgentKey, { label: string; role: string }> = {
  orchestrator: { label: "Orchestrator", role: "파이프라인 제어" },
  generator: { label: "Generator", role: "처방 초안 생성" },
  validator: { label: "Validator", role: "안전성 검증" },
  corrector: { label: "Corrector", role: "위반 자동 교정" },
  reporter: { label: "Reporter", role: "검수 리포트 작성" },
};

export interface AnimatedStep {
  agent: AgentKey;
  label: string;
  attempt?: number;
}
