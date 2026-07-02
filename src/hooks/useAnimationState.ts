import { useState } from "react";
import type { PatientData, AnimatedStep } from "../types";
import { ANIMATION_TIMINGS } from "../data/agents";

export function useAnimationState() {
  const [isRunning, setIsRunning] = useState(false);
  const [revealedSteps, setRevealedSteps] = useState<AnimatedStep[]>([]);
  const [currentPatient, setCurrentPatient] = useState<PatientData | null>(null);
  const [showSoap, setShowSoap] = useState(false);

  const startPipeline = (data: PatientData) => {
    setCurrentPatient(data);
    setIsRunning(true);
    setRevealedSteps([]);
    setShowSoap(false);

    // Orchestrator
    setTimeout(() => {
      setRevealedSteps([
        {
          agent: "orchestrator",
          label: "환자 재활 안전성 검증 파이프라인 스케줄링 및 리소스 할당 완료",
        },
      ]);
    }, ANIMATION_TIMINGS.ORCHESTRATOR);

    // Generator
    setTimeout(() => {
      setRevealedSteps((prev) => [
        ...prev,
        {
          agent: "generator",
          label: `${data.surgery} 기반 맞춤형 재활 운동 프로토콜 초안 설계 완료`,
        },
      ]);
    }, ANIMATION_TIMINGS.GENERATOR);

    // Validator
    setTimeout(() => {
      setRevealedSteps((prev) => [
        ...prev,
        {
          agent: "validator",
          label: `회복 주차(${data.week}주) 대비 운동 강도 및 ROM 금기 요소 교차 검증 통과`,
        },
      ]);
    }, ANIMATION_TIMINGS.VALIDATOR);

    // Corrector
    setTimeout(() => {
      setRevealedSteps((prev) => [
        ...prev,
        {
          agent: "corrector",
          label: "미세 조정 및 임상적 안전성 최종 보정 완료",
        },
      ]);
    }, ANIMATION_TIMINGS.CORRECTOR);

    // Reporter
    setTimeout(() => {
      setRevealedSteps((prev) => [
        ...prev,
        {
          agent: "reporter",
          label: "의학적 근거 중심의 안전성 검증 리포트 추출 완료",
        },
      ]);
      setIsRunning(false);
    }, ANIMATION_TIMINGS.REPORTER);

    // Show SOAP
    setTimeout(() => {
      setShowSoap(true);
    }, ANIMATION_TIMINGS.SOAP_REVEAL);
  };

  return {
    isRunning,
    revealedSteps,
    currentPatient,
    showSoap,
    startPipeline,
  };
}
