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
    { agent: "info-extractor", label: "환자 입력 구조화 + notes 마스킹 + 스코프 판정 (extract_redact.py)" },
  ];

  if (result.status === "unsupported_surgery" || result.status === "manual_review_required") {
    return steps;
  }

  steps.push({
    agent: "rag-recommender",
    label: "프로토콜 근거 컨텍스트(fetch_protocol) + 단계 적합 후보 검색(retrieve)",
  });

  if (result.status === "insufficient_evidence") {
    return steps;
  }

  if (result.status === "red_flag") {
    steps.push({
      agent: "safety-judge",
      label: "🚩 Gate 1 안전성 검증: hard 위반 ≥ 11건 — Red Flag 즉시 종료",
    });
    return steps;
  }

  steps.push({
    agent: "safety-judge",
    label: result.correctionUsed
      ? "Gate 1 안전성 검증: 위반 발견 (safety_judge --mode safety)"
      : "Gate 1 안전성 검증 통과: 위반 0건",
  });

  if (result.correctionUsed) {
    steps.push({
      agent: "corrector",
      label: "위반 항목 자동 교정(등척성 치환/제외/필터) + 재검색",
    });
    steps.push({
      agent: "safety-judge",
      label: `재검증 통과 (총 ${result.iterations}회 반복)`,
    });
  }

  if (result.status !== "ready_for_reporter") {
    return steps;
  }

  steps.push({ agent: "prescription-generator", label: "안전 통과 후보로 처방 3개 조립 (generate_rx.py)" });
  steps.push({
    agent: "safety-judge",
    label: "완결성 재검증 (safety_judge --mode completeness)",
  });
  steps.push({ agent: "report-writer", label: "이중언어 SOAP 서술 작성 (reporter — LLM)" });
  steps.push({ agent: "report-validator", label: "Gate 3 기계 검증: 개수·필드·이중언어·길이 (report_validate.py)" });
  steps.push({ agent: "report-judge", label: "Gate 2 판단: 서술 품질(J1) · 근거성(J4) 통과 (report_judge — LLM)" });
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

      <footer className="mt-12 border-t-2 border-gray-300 bg-gray-50 py-8">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <p className="text-sm font-bold text-gray-900">
            ⚠ 본 서비스 사용에 따른 모든 책임은 사용자에게 있습니다.
          </p>
          <p className="mt-2 text-xs text-gray-500">
            © 2026 Upstage Education. Harness Engineering 프로젝트 데모 — 실제 임상 사용 불가.
          </p>
        </div>
      </footer>
    </div>
  );
}
