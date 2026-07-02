import type { AgentKey } from "../types";

export const ANIMATION_TIMINGS = {
  ORCHESTRATOR: 500,
  GENERATOR: 1500,
  VALIDATOR: 2800,
  CORRECTOR: 4000,
  REPORTER: 5200,
  SOAP_REVEAL: 6500,
};

export const AGENT_META: Record<AgentKey, { name: string; label: string; color: string; icon: string }> = {
  orchestrator: {
    name: "Orchestrator",
    label: "Orchestrator",
    color: "brand",
    icon: "Zap",
  },
  generator: {
    name: "Generator",
    label: "Generator",
    color: "blue",
    icon: "Sparkles",
  },
  validator: {
    name: "Validator",
    label: "Validator",
    color: "safe",
    icon: "CheckCircle2",
  },
  corrector: {
    name: "Corrector",
    label: "Corrector",
    color: "warning",
    icon: "Settings",
  },
  reporter: {
    name: "Reporter",
    label: "Reporter",
    color: "brand",
    icon: "FileText",
  },
};

export const AGENT_ORDER: AgentKey[] = [
  "orchestrator",
  "generator",
  "validator",
  "corrector",
  "reporter",
];
