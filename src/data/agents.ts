// 실제 파이프라인(saferx-v2/scripts/run_pipeline.py + rag/harness_runner.py) 흐름과 1:1 매핑.
// 시각화 노드는 스크립트 호출 순서를 그대로 반영: fetch_protocol과 완결성 재검(Gate 1 두번째 호출)은
// safety-judge/rag-recommender 노드에 병합하지 않고 flow(App.tsx buildAnimatedSteps)에서 표기한다.

export type AgentKey =
  | "info-extractor"
  | "rag-recommender"
  | "safety-judge"
  | "corrector"
  | "prescription-generator"
  | "report-writer"
  | "report-validator"
  | "report-judge";

export const AGENT_ORDER: AgentKey[] = [
  "info-extractor",
  "rag-recommender",
  "safety-judge",
  "corrector",
  "prescription-generator",
  "report-writer",
  "report-validator",
  "report-judge",
];

export const AGENT_META: Record<AgentKey, { label: string; role: string }> = {
  "info-extractor": { label: "정보추출", role: "입력 구조화 + 마스킹 (extract_redact)" },
  "rag-recommender": { label: "RAG 추천", role: "프로토콜 후보 검색 (retrieve + fetch_protocol)" },
  "safety-judge": { label: "Safety Judge", role: "Gate 1 규칙표 대조 (safety + completeness)" },
  corrector: { label: "Corrector", role: "위반 자동 교정 후 재검색" },
  "prescription-generator": { label: "Generator", role: "처방 5개 조립 (verbatim)" },
  "report-writer": { label: "Reporter", role: "SOAP 이중언어 서술 (LLM)" },
  "report-validator": { label: "Gate 3", role: "리포트 기계 검증 (J2/J3/J5/J6)" },
  "report-judge": { label: "Report Judge", role: "Gate 2 언어 판단 (J1/J4, LLM)" },
};

export interface AnimatedStep {
  agent: AgentKey;
  label: string;
}
