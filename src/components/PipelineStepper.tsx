import { AGENT_META, AGENT_ORDER, type AnimatedStep } from "../data/agents";
import type { AgentKey } from "../types";

interface Props {
  revealedSteps: AnimatedStep[];
  isRunning: boolean;
}

function nodeStatus(agent: AgentKey, revealedSteps: AnimatedStep[], isRunning: boolean): "pending" | "active" | "done" {
  if (revealedSteps.length === 0) return "pending";
  const lastStep = revealedSteps[revealedSteps.length - 1];
  const hasVisited = revealedSteps.some((s) => s.agent === agent);
  if (isRunning && lastStep.agent === agent) return "active";
  return hasVisited ? "done" : "pending";
}

export default function PipelineStepper({ revealedSteps, isRunning }: Props) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">파이프라인 진행 상태</h2>
      <p className="mt-1 text-sm text-gray-500">
        생성 → 검증 → (위반 시) 자동 교정·재검증 최대 2회 → 리포트 출력
      </p>

      <div className="mt-6 flex items-center">
        {AGENT_ORDER.map((agent, i) => {
          const status = nodeStatus(agent, revealedSteps, isRunning);
          return (
            <div key={agent} className="flex flex-1 items-center last:flex-initial">
              <div className="flex flex-col items-center gap-2">
                <div
                  className={
                    "flex h-11 w-11 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors " +
                    (status === "active"
                      ? "border-blue-600 bg-blue-600 text-white animate-pulse"
                      : status === "done"
                        ? "border-emerald-500 bg-emerald-50 text-emerald-600"
                        : "border-gray-200 bg-gray-50 text-gray-400")
                  }
                >
                  {status === "done" ? "✓" : i + 1}
                </div>
                <span
                  className={
                    "text-xs font-medium whitespace-nowrap " +
                    (status === "pending" ? "text-gray-400" : "text-gray-700")
                  }
                >
                  {AGENT_META[agent].label}
                </span>
              </div>
              {i < AGENT_ORDER.length - 1 && (
                <div
                  className={
                    "mx-2 h-0.5 flex-1 rounded transition-colors " +
                    (status === "done" ? "bg-emerald-400" : "bg-gray-200")
                  }
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 max-h-56 space-y-2 overflow-y-auto">
        {revealedSteps.length === 0 && (
          <p className="text-sm text-gray-400">입력 폼을 제출하면 실행 로그가 여기에 표시됩니다.</p>
        )}
        {revealedSteps.map((step, i) => {
          const isLast = i === revealedSteps.length - 1;
          const stillRunning = isLast && isRunning;
          return (
            <div
              key={`${step.agent}-${i}`}
              className="flex items-center gap-3 rounded-lg bg-gray-50 px-3 py-2 text-sm"
            >
              <span className="inline-flex w-24 shrink-0 items-center rounded-md bg-white px-2 py-0.5 text-xs font-semibold text-gray-600 ring-1 ring-gray-200">
                {AGENT_META[step.agent].label}
              </span>
              <span className="flex-1 text-gray-700">
                {step.label}
                {step.attempt ? ` (시도 ${step.attempt}회)` : ""}
              </span>
              <span className={"text-xs font-medium " + (stillRunning ? "text-blue-600" : "text-emerald-600")}>
                {stillRunning ? "진행 중…" : "완료"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
