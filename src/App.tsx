import { useRef, useState } from "react";
import { runPipeline } from "./api/harness";
import Header from "./components/Header";
import PatientForm from "./components/PatientForm";
import PipelineStepper from "./components/PipelineStepper";
import ValidationReport from "./components/ValidationReport";
import type { AnimatedStep } from "./data/agents";
import type { PatientInput, PipelineResult } from "./types";

type RunState = "idle" | "running" | "done" | "error";

const STEP_DELAY_MS = 480;

function buildAnimatedSteps(result: PipelineResult): AnimatedStep[] {
  const steps: AnimatedStep[] = [{ agent: "extractor", label: "환자 입력을 구조화된 필드로 파싱" }];

  result.attempts.forEach((attempt, i) => {
    if (i === 0) {
      steps.push({
        agent: "rag",
        label: "ChromaDB(ACL 프로토콜)에서 회복 단계에 맞는 운동 검색",
        attempt: attempt.attempt,
      });
    } else {
      steps.push({
        agent: "corrector",
        label: "위반 피드백을 반영해 제외 목록·필터 갱신 후 RAG 재검색",
        attempt: attempt.attempt - 1,
      });
    }
    steps.push({
      agent: "judge",
      label:
        attempt.issues.length === 0
          ? "규칙표 대조 검증 완료: 위반 0건"
          : `규칙표 대조 검증: 위반 ${attempt.issues.length}건 발견`,
      attempt: attempt.attempt,
    });
  });

  steps.push({ agent: "generator", label: "검증 통과 항목으로 최종 처방 생성" });
  steps.push({ agent: "reporter", label: "근거·출처를 포함한 검수 리포트 작성" });
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
