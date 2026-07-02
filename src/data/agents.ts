import type { AgentKey } from "../types";

export const AGENT_ORDER: AgentKey[] = ["extractor", "rag", "judge", "corrector", "generator", "reporter"];

export const AGENT_META: Record<AgentKey, { label: string; role: string }> = {
  extractor: { label: "정보추출", role: "환자 입력 구조화" },
  rag: { label: "RAG 추천", role: "PT 프로토콜 검색" },
  judge: { label: "Judge", role: "규칙표 대조 검증" },
  corrector: { label: "Corrector", role: "위반 자동 교정" },
  generator: { label: "Generator", role: "최종 처방 생성" },
  reporter: { label: "Reporter", role: "검수 리포트 작성" },
};

export interface AnimatedStep {
  agent: AgentKey;
  label: string;
  attempt?: number;
}
