export type AgentKey =
  | "info-extractor"
  | "rag-recommender"
  | "safety-judge"
  | "corrector"
  | "prescription-generator"
  | "report-writer"
  | "report-judge";

export const AGENT_ORDER: AgentKey[] = [
  "info-extractor",
  "rag-recommender",
  "safety-judge",
  "corrector",
  "prescription-generator",
  "report-writer",
  "report-judge",
];

export const AGENT_META: Record<AgentKey, { label: string; role: string }> = {
  "info-extractor": { label: "정보추출", role: "입력 구조화 + 마스킹" },
  "rag-recommender": { label: "RAG 추천", role: "프로토콜 후보 검색" },
  "safety-judge": { label: "Safety Judge", role: "규칙표 대조 검증 (Gate 1)" },
  corrector: { label: "Corrector", role: "위반 자동 교정" },
  "prescription-generator": { label: "Generator", role: "처방 3개 조립" },
  "report-writer": { label: "Reporter", role: "SOAP 서술 작성" },
  "report-judge": { label: "Report Judge", role: "리포트 품질 검수 (Gate 2)" },
};

export interface AnimatedStep {
  agent: AgentKey;
  label: string;
}
