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
    <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-md h-full flex flex-col justify-between">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">파이프라인 진행 상태</h2>
        <p className="mt-1 text-sm text-gray-500">
          생성 → 검증 → (위반 시) 자동 교정·재검증 최대 2회 → 리포트 출력
        </p>

        {/* 스테퍼 인디케이터 컬러 브랜드화 */}
        <div className="mt-6 flex items-center">
          {AGENT_ORDER.map((agent, i) => {
            const status = nodeStatus(agent, revealedSteps, isRunning);
            return (
              <div key={agent} className="flex flex-1 items-center last:flex-initial">
                <div className="flex flex-col items-center gap-2">
                  <div
                    className={
                      "flex h-11 w-11 items-center justify-center rounded-full border-2 text-sm font-bold transition-all duration-300 " +
                      (status === "active"
                        ? "border-[#00BAA4] bg-[#00BAA4] text-white animate-pulse shadow-lg shadow-[#00BAA4]/20"
                        : status === "done"
                          ? "border-emerald-500 bg-emerald-50 text-emerald-600"
                          : "border-gray-200 bg-gray-50 text-gray-400")
                    }
                  >
                    {status === "done" ? "✓" : i + 1}
                  </div>
                  <span
                    className={
                      "text-xs font-semibold whitespace-nowrap " +
                      (status === "pending" ? "text-gray-400" : "text-slate-700")
                    }
                  >
                    {AGENT_META[agent].label}
                  </span>
                </div>
                {i < AGENT_ORDER.length - 1 && (
                  <div
                    className={
                      "mx-2 h-0.5 flex-1 rounded transition-colors duration-500 " +
                      (status === "done" ? "bg-emerald-400" : "bg-gray-200")
                    }
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 하단 컨텐츠 가독성 고도화 및 최소 세로폭 유지 */}
      <div className="mt-6 flex-1 min-h-[260px] flex flex-col justify-start overflow-y-auto pr-1">
        {revealedSteps.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full content-start animate-fadeIn">
            <div className="col-span-1 md:col-span-2 text-xs font-bold text-slate-400 mb-1 flex items-center gap-1.5 select-none">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00BAA4] animate-pulse"></span>
              시스템 가동 대기 중: 하네스 멀티 에이전트 핵심 명세
            </div>
            
            <div className="border border-slate-100 bg-slate-50/60 rounded-xl p-3 text-xs flex flex-col gap-1 hover:border-slate-200 transition-colors">
              <span className="font-bold text-slate-800 text-[13px]">1. Orchestrator <span className="text-slate-400 font-normal">(중재)</span></span>
              <p className="text-slate-500 leading-relaxed text-[11px]">전체 안전성 검증 파이프라인의 작업 흐름을 최적화하고 스케줄링 수행.</p>
            </div>
            
            <div className="border border-slate-100 bg-slate-50/60 rounded-xl p-3 text-xs flex flex-col gap-1 hover:border-slate-200 transition-colors">
              <span className="font-bold text-slate-800 text-[13px]">2. Generator <span className="text-slate-400 font-normal">(생성)</span></span>
              <p className="text-slate-500 leading-relaxed text-[11px]">입력된 환자 메타데이터에 가장 적합한 임상용 재활 운동 처방 초안 설계.</p>
            </div>
            
            <div className="border border-slate-100 bg-slate-50/60 rounded-xl p-3 text-xs flex flex-col gap-1 hover:border-slate-200 transition-colors">
              <span className="font-bold text-slate-800 text-[13px]">3. Validator <span className="text-slate-400 font-normal">(검증)</span></span>
              <p className="text-slate-500 leading-relaxed text-[11px]">임상 가이드라인 가이드를 바탕으로 수술 부위별 위험 금기 요소를 전면 필터링.</p>
            </div>
            
            <div className="border border-slate-100 bg-slate-50/60 rounded-xl p-3 text-xs flex flex-col gap-1 hover:border-slate-200 transition-colors">
              <span className="font-bold text-slate-800 text-[13px]">4. Corrector <span className="text-slate-400 font-normal">(교정)</span></span>
              <p className="text-slate-500 leading-relaxed text-[11px]">기준 위반 감지 시 실시간 피드백 루프를 가동하여 자동 교정 및 재심사 진행.</p>
            </div>
            
            <div className="border border-slate-100 bg-slate-50/60 rounded-xl p-3 text-xs flex flex-col gap-1 md:col-span-2 hover:border-slate-200 transition-colors">
              <span className="font-bold text-slate-800 text-[13px]">5. Reporter <span className="text-slate-400 font-normal">(리포트 발행)</span></span>
              <p className="text-slate-500 leading-relaxed text-[11px]">검증을 최종 통과한 안전성 보장형 의학적 근거 중심 처방 결과 검수 보고서 추출.</p>
            </div>
          </div>
        ) : (
          <div className="space-y-2.5 w-full animate-fadeIn">
            {revealedSteps.map((step, i) => {
              const isLast = i === revealedSteps.length - 1;
              const stillRunning = isLast && isRunning;
              return (
                <div
                  key={`${step.agent}-${i}`}
                  className="flex items-center gap-3 rounded-xl bg-slate-50/80 border border-slate-100 px-3 py-2.5 text-sm transition-all"
                >
                  <span className="inline-flex w-24 shrink-0 items-center justify-center rounded-md bg-white border border-slate-200 py-0.5 text-xs font-bold text-slate-700 shadow-sm">
                    {AGENT_META[step.agent].label}
                  </span>
                  <span className="flex-1 text-slate-700 font-medium text-[13px]">
                    {step.label}
                    {step.attempt ? ` (시도 ${step.attempt}회)` : ""}
                  </span>
                  <span className={"text-xs font-bold " + (stillRunning ? "text-[#00BAA4] animate-pulse" : "text-emerald-600")}>
                    {stillRunning ? "진행 중…" : "완료"}
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