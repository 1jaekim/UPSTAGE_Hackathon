import { useRef, useState } from "react";
import Header from "./components/Header";
import PatientForm from "./components/PatientForm";
import PipelineStepper from "./components/PipelineStepper";
import ValidationReport from "./components/ValidationReport";
import type { AnimatedStep } from "./data/agents";
import { runPipeline } from "./engine/pipeline";
import type { PatientInput, PipelineResult } from "./types";

type RunState = "idle" | "running" | "done";

const STEP_DELAY_MS = 480;

function buildAnimatedSteps(result: PipelineResult): AnimatedStep[] {
  const steps: AnimatedStep[] = [{ agent: "orchestrator", label: "파이프라인 시작: 생성 → 검증 → 교정 순서 실행" }];

  result.attempts.forEach((attempt, i) => {
    if (i === 0) {
      steps.push({ agent: "generator", label: "수술명·주차·환자정보로 단계별 처방 초안 생성", attempt: attempt.attempt });
    } else {
      steps.push({ agent: "corrector", label: "위반 항목 피드백을 반영해 처방 재생성", attempt: attempt.attempt - 1 });
    }
    steps.push({
      agent: "validator",
      label:
        attempt.issues.length === 0
          ? "규칙표 대조 검증 완료: 위반 0건"
          : `규칙표 대조 검증: 위반 ${attempt.issues.length}건 발견`,
      attempt: attempt.attempt,
    });
  });

  steps.push({ agent: "reporter", label: "위반·교정 내역과 규칙 근거를 검수 리포트로 정리" });
  return steps;
}

export default function App() {
  const [runState, setRunState] = useState<RunState>("idle");
  const [revealedSteps, setRevealedSteps] = useState<AnimatedStep[]>([]);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const runIdRef = useRef(0);

  function handleSubmit(input: PatientInput) {
    const runId = ++runIdRef.current;
    setRunState("running");
    setResult(null);
    setRevealedSteps([]);

    const pipelineResult = runPipeline(input);
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
            <PipelineStepper revealedSteps={revealedSteps} isRunning={runState === "running"} />
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
