import { CheckCircle2, Zap } from "lucide-react";
import { AGENT_META, AGENT_ORDER } from "../data/agents";
import type { AnimatedStep, AgentKey } from "../types";

interface Props {
  revealedSteps: AnimatedStep[];
  isRunning: boolean;
}

function getNodeStatus(
  agent: AgentKey,
  revealedSteps: AnimatedStep[],
  isRunning: boolean
): "pending" | "active" | "done" {
  if (revealedSteps.length === 0) return "pending";
  const lastStep = revealedSteps[revealedSteps.length - 1];
  const hasVisited = revealedSteps.some((s) => s.agent === agent);
  if (isRunning && lastStep.agent === agent) return "active";
  return hasVisited ? "done" : "pending";
}

export default function PipelineStepper({ revealedSteps, isRunning }: Props) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-md h-full flex flex-col justify-between">
      
      {/* 헤더 */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-slate-900">파이프라인 진행 상태</h2>
        <p className="mt-1 text-xs text-slate-500">
          생성 → 검증 → (위반 시) 자동 교정·재검증 → 리포트 출력
        </p>

        {/* 진행도 바 */}
        {revealedSteps.length > 0 && (
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-700">
                {revealedSteps.length} / 5 단계 완료
              </span>
              <span className="text-slate-500">
                {Math.round((revealedSteps.length / 5) * 100)}%
              </span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r rounded-full transition-all duration-1000 ease-out"
                style={{
                  width: `${(revealedSteps.length / 5) * 100}%`,
                  background: "linear-gradient(to right, var(--color-brand, #00BAA4), var(--color-safe, #10B981))"
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* 스테퍼 인디케이터 */}
      <div className="mt-6">
        <div className="flex items-center justify-between">
          {AGENT_ORDER.map((agent, i) => {
            const status = getNodeStatus(agent, revealedSteps, isRunning);
            const isLast = i === AGENT_ORDER.length - 1;
            const meta = AGENT_META[agent];
            const agentColor = `var(--color-${agent}, #00BAA4)`;

            return (
              <div key={agent} className="flex flex-col items-center flex-1">
                {/* 노드 */}
                <div className="flex flex-col items-center gap-2 mb-3 w-full">
                  <div
                    className={`flex h-12 w-12 items-center justify-center rounded-full border-2 font-bold text-sm transition-all duration-500 relative ${
                      status === "active"
                        ? "animate-pulse"
                        : status === "done"
                          ? "bg-emerald-50"
                          : "bg-slate-50"
                    }`}
                    style={{
                      borderColor: status === "active" || status === "done" ? agentColor : "var(--color-slate-300, #cbd5e1)",
                      backgroundColor: status === "active" 
                        ? agentColor 
                        : status === "done"
                          ? "var(--color-safe, #10B981)/10"
                          : "var(--color-slate-50, #f8fafc)",
                      color: status === "active" 
                        ? "white" 
                        : status === "done"
                          ? "var(--color-safe, #10B981)"
                          : "var(--color-slate-400, #94a3b8)",
                      boxShadow: status === "active" ? `0 0 20px ${agentColor}40` : "none"
                    }}
                  >
                    {status === "done" ? (
                      <CheckCircle2 className="w-6 h-6 animate-popIn" />
                    ) : status === "active" ? (
                      <Zap className="w-5 h-5 animate-bounce" />
                    ) : (
                      <span>{i + 1}</span>
                    )}
                  </div>

                  {/* 라벨 */}
                  <span
                    className={`text-xs font-semibold whitespace-nowrap transition-colors duration-300 ${
                      status === "pending"
                        ? "text-slate-400"
                        : status === "active"
                          ? "font-bold"
                          : "text-slate-700"
                    }`}
                    style={
                      status === "active"
                        ? { color: agentColor }
                        : {}
                    }
                  >
                    {meta.label}
                  </span>
                </div>

                {/* 커넥팅 라인 */}
                {!isLast && (
                  <div
                    className={`h-1 flex-1 mb-3 rounded transition-all duration-500 ${
                      status === "done" ? "" : ""
                    }`}
                    style={{
                      margin: "0 4px",
                      minWidth: "20px",
                      backgroundColor: status === "done" 
                        ? "var(--color-safe, #10B981)" 
                        : "var(--color-slate-200, #e2e8f0)",
                      animation: status === "done" ? "slideRight 600ms ease-out forwards" : "none"
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 단계별 진행 로그 */}
      <div className="mt-8 flex-1 min-h-[200px] flex flex-col justify-start overflow-y-auto scrollbar-thin">
        {revealedSteps.length === 0 ? (
          <div className="grid grid-cols-1 gap-2 animate-fadeIn">
            <div className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1.5">
              <span 
                className="w-1.5 h-1.5 rounded-full animate-pulse"
                style={{ backgroundColor: "var(--color-brand, #00BAA4)" }}
              />
              시스템 대기 중
            </div>
            {[
              { color: "var(--color-generator, #3B82F6)", label: "Orchestrator", desc: "전체 파이프라인 작업 흐름을 최적화하고 리소스를 할당합니다." },
              { color: "var(--color-validator, #F97316)", label: "Generator", desc: "환자 데이터를 기반으로 임상용 재활 운동 처방을 설계합니다." },
              { color: "var(--color-corrector, #8B5CF6)", label: "Validator", desc: "임상 가이드라인을 기반으로 수술 부위별 금기 사항을 검증합니다." }
            ].map((item, idx) => (
              <div 
                key={idx}
                className="rounded-lg p-3 text-xs border"
                style={{
                  backgroundColor: `${item.color}10`,
                  borderColor: `${item.color}30`
                }}
              >
                <p className="font-semibold text-slate-800 mb-1">{item.label}</p>
                <p style={{ color: `${item.color}90` }} className="text-[11px]">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2 animate-fadeIn">
            {revealedSteps.map((step, i) => {
              const isLastStep = i === revealedSteps.length - 1;
              const isStillRunning = isLastStep && isRunning;
              const agentColor = `var(--color-${step.agent}, #00BAA4)`;

              return (
                <div
                  key={`${step.agent}-${i}`}
                  className="flex items-start gap-3 rounded-xl border p-3 hover:border-slate-200 hover:shadow-sm transition-all duration-300 animate-slideIn bg-gradient-to-r"
                  style={{
                    backgroundColor: "rgba(248, 250, 252, 0.5)",
                    borderColor: "var(--color-slate-200, #e2e8f0)",
                    backgroundImage: "linear-gradient(to right, rgba(248, 250, 252, 0.5), rgba(248, 250, 252, 0.5))"
                  }}
                >
                  {/* 상태 아이콘 */}
                  <div className="flex-shrink-0 pt-0.5">
                    {isStillRunning ? (
                      <div 
                        className="w-5 h-5 rounded-full border-2 border-t-transparent animate-spin"
                        style={{
                          borderColor: `${agentColor}40`,
                          borderTopColor: agentColor
                        }}
                      />
                    ) : (
                      <CheckCircle2 className="w-5 h-5 flex-shrink-0" style={{ color: "var(--color-safe, #10B981)" }} />
                    )}
                  </div>

                  {/* 콘텐츠 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span 
                        className="inline-flex px-2 py-1 rounded-md text-xs font-bold whitespace-nowrap"
                        style={{
                          backgroundColor: `${agentColor}15`,
                          color: agentColor
                        }}
                      >
                        {AGENT_META[step.agent].label}
                      </span>
                      {step.attempt && (
                        <span className="text-xs text-slate-500">
                          (시도 {step.attempt}회)
                        </span>
                      )}
                    </div>
                    <p className="text-slate-700 font-medium text-xs leading-relaxed">
                      {step.label}
                    </p>
                  </div>

                  {/* 상태 텍스트 */}
                  <span
                    className={`text-xs font-bold whitespace-nowrap flex-shrink-0 ${
                      isStillRunning ? "animate-pulse" : ""
                    }`}
                    style={{
                      color: isStillRunning ? agentColor : "var(--color-safe, #10B981)"
                    }}
                  >
                    {isStillRunning ? "진행 중…" : "✓"}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
