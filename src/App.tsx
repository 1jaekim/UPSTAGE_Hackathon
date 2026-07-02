import { useRef, useState } from "react";
import { runPipeline } from "./api/harness";
import Header from "./components/Header";
import PatientForm from "./components/PatientForm";
import PipelineStepper from "./components/PipelineStepper";
import ValidationReport from "./components/ValidationReport";
import type { AnimatedStep } from "./data/agents";
import type { PatientInput, PipelineResult } from "./types";

type RunState = "idle" | "running" | "done" | "error";

const STEP_DELAY_MS = 420;

function buildAnimatedSteps(result: PipelineResult): AnimatedStep[] {
  const steps: AnimatedStep[] = [
    { agent: "info-extractor", label: "환자 입력 구조화 통과 + notes 마스킹 + 스코프 판정" },
  ];

  if (result.status === "unsupported_surgery" || result.status === "manual_review_required") {
    return steps;
  }

  steps.push({ agent: "rag-recommender", label: "프로토콜 라이브러리에서 단계에 맞는 후보 검색" });

  if (result.status === "insufficient_evidence") {
    return steps;
  }

  steps.push({
    agent: "safety-judge",
    label: result.correctionUsed ? "규칙표 대조 검증: 위반 발견" : "규칙표 대조 검증 완료: 위반 0건",
  });

  if (result.correctionUsed) {
    steps.push({ agent: "corrector", label: "위반 항목 자동 교정(등척성 치환/제외/필터) 후 재검색" });
    steps.push({ agent: "safety-judge", label: `재검증 완료 (총 ${result.iterations}회 반복)` });
  }

  if (result.status !== "ready_for_reporter") {
    return steps;
  }

  steps.push({ agent: "prescription-generator", label: "안전성 통과 항목으로 처방 5개 조립" });
  steps.push({ agent: "report-writer", label: "SOAP 형식 검수 리포트 서술 작성 (이중언어)" });
  steps.push({ agent: "report-judge", label: "리포트 품질·근거 일치 검수 통과" });
  return steps;
}

export default function App() {
  const [runState, setRunState] = useState<RunState>("idle");
  const [revealedSteps, setRevealedSteps] = useState<AnimatedStep[]>([]);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const runIdRef = useRef(0);

  async function handleSubmit(input: PatientInput) {
    const runId = ++runIdRef.current;
    setRunState("running");
    setResult(null);
    setErrorMessage(null);
    setRevealedSteps([]);

    let pipelineResult: PipelineResult;
    try {
      pipelineResult = await runPipeline(input);
    } catch (err) {
      if (runIdRef.current !== runId) return;
      setErrorMessage(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
      setRunState("error");
      return;
    }
    if (runIdRef.current !== runId) return;

    const allSteps = buildAnimatedSteps(pipelineResult);
    allSteps.forEach((step, i) => {
      setTimeout(() => {
        if (runIdRef.current !== runId) return;
        setRevealedSteps((prev) => [...prev, step]);
        if (i === allSteps.length - 1) {
          setTimeout(() => {
            if (runIdRef.current !== runId) return;
            setResult(pipelineResult);
            setRunState("done");
          }, STEP_DELAY_MS);
        }
      }, STEP_DELAY_MS * (i + 1));
    });
  }

  return (
    <div className="min-h-screen bg-white">
      <Header />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
          <div className="lg:sticky lg:top-8 lg:self-start">
            <PatientForm disabled={runState === "running"} onSubmit={handleSubmit} />
          </div>

          <div className="space-y-6">
            {runState === "error" && errorMessage && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                <span className="font-semibold">실행 실패:</span> {errorMessage}
              </div>
            )}
            {runState !== "error" && (
              <PipelineStepper revealedSteps={revealedSteps} isRunning={runState === "running"} />
            )}
            {runState === "done" && result && <ValidationReport result={result} />}
          </div>
        </div>
      </main>

      <footer className="mt-12 border-t border-gray-200 bg-white py-6">
        <div className="mx-auto max-w-6xl px-6 text-xs text-gray-400">
          © 2026 Upstage Education. Harness Engineering 프로젝트 데모 — 실제 임상 사용 불가.
        </div>
      </footer>
    </div>
  );
}
