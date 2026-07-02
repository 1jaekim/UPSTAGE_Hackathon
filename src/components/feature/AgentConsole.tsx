import { useEffect, useState, useRef, useMemo } from "react";
import { Circle } from "lucide-react";
import { AGENT_META, AGENT_ORDER } from "../../data/agents";
import type { AnimatedStep, AgentKey } from "../../types";

interface Props {
  revealedSteps: AnimatedStep[];
}

export default function AgentConsole({ revealedSteps }: Props) {
  const [consoleLogs, setConsoleLogs] = useState<Array<{ text: string; type: AgentKey | "system" | "success" }>>([]);
  const consoleEndRef = useRef<HTMLDivElement>(null);

  const getTimestamp = () => {
    const now = new Date();
    return now.toTimeString().split(" ")[0];
  };

  const getLogColor = (type: AgentKey | "system" | "success"): string => {
    if (type === "system") return "text-slate-300";
    if (type === "success") return "text-cyan-400";
    return `text-[var(--color-${type}, #00BAA4)]`;
  };

  useEffect(() => {
    setConsoleLogs([
      { text: `[${getTimestamp()}] Harness Engineering 안전성 검증 커널 초기화 완료.`, type: "system" },
      { text: `[${getTimestamp()}] Orchestrator Agent: 대기 상태 (환자 처방 입력을 기다리는 중...)`, type: "orchestrator" },
      { text: `[${getTimestamp()}] 시스템 연결 성공: 물리치료 데이터 파이프라인 준비 완료.`, type: "system" },
      { text: `▶ System ready`, type: "success" }
    ]);
  }, []);

  useEffect(() => {
    if (revealedSteps.length === 0) return;

    const latestStep = revealedSteps[revealedSteps.length - 1];
    const time = `[${getTimestamp()}]`;

    if (revealedSteps.length === 1 && latestStep.agent === "orchestrator") {
      setConsoleLogs([
        { text: `${time} [⚙️ System] 파이프라인 트리거 수신 - 임상 데이터 세션 초기화 완료.`, type: "system" },
        { text: `${time} [Orchestrator] 에이전트 군집(Swarm) 리소스 할당 완료. 작업 스케줄링을 시작합니다.`, type: "orchestrator" }
      ]);
      return;
    }

    let agentLog = "";
    let logType: AgentKey | "system" | "success" = latestStep.agent;

    switch (latestStep.agent) {
      case "generator":
        agentLog = `${time} [Generator] 임상 규칙 모델 데이터 로딩 완료 ➡️ 환자 맞춤형 처방 시퀀스 매핑 중...`;
        break;
      case "validator":
        agentLog = `${time} [Validator] 관절 가동 범위(ROM) 및 수술 부위별 금기 조항 교차 검증 엔진 구동 ➡️ 이상 없음.`;
        break;
      case "corrector":
        agentLog = `${time} [Corrector] 파이프라인 검수 완료 ➡️ 예외 사항 제로, 가이드라인 최종 정합성 보정 완료.`;
        break;
      case "reporter":
        agentLog = `${time} [Reporter] 의학적 근거 중심의 안전성 처방 검수 결과보고서(PDF) 디지털 발행 완료.`;
        break;
    }

    if (agentLog) {
      if (latestStep.agent === "reporter") {
        setConsoleLogs((prev) => [
          ...prev,
          { text: agentLog, type: logType },
          { text: `▶ Pipeline execution completed successfully. System idle.`, type: "success" }
        ]);
      } else {
        setConsoleLogs((prev) => [...prev, { text: agentLog, type: logType }]);
      }
    }
  }, [revealedSteps]);

  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [consoleLogs]);

  const pipelineProgress = useMemo(() => {
    const total = 5;
    const completed = revealedSteps.length;
    return { completed, total, percentage: (completed / total) * 100 };
  }, [revealedSteps]);

  return (
    <div 
      className="text-slate-200 rounded-2xl p-5 font-mono text-xs shadow-inner border border-slate-900/50 flex flex-col gap-4 hover:border-slate-800 transition-colors duration-300"
      style={{ backgroundColor: "#0B132B" }}
    >
      {/* 헤더 */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 select-none">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <Circle className="w-2.5 h-2.5 fill-red-500 text-red-500" />
            <Circle className="w-2.5 h-2.5 fill-yellow-500 text-yellow-500" />
            <Circle className="w-2.5 h-2.5 fill-green-500 text-green-500" />
          </div>
          <span className="text-slate-400 font-semibold ml-2 tracking-wide">
            Agent Executive Console
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span 
            className="w-1.5 h-1.5 rounded-full animate-pulse"
            style={{ backgroundColor: "var(--color-brand, #00BAA4)" }}
          />
          <span 
            className="text-[10px] font-bold tracking-widest uppercase"
            style={{ color: "var(--color-brand, #00BAA4)" }}
          >
            Live
          </span>
        </div>
      </div>

      {/* 메인 콘솔 + 메트릭 */}
      <div className="flex flex-col lg:flex-row gap-6 h-[280px] overflow-hidden">
        {/* 좌측: 콘솔 로그 */}
        <div className="flex-1 space-y-1.5 overflow-y-auto leading-relaxed pr-2 text-slate-300 scrollbar-thin">
          {consoleLogs.map((log, index) => (
            <div
              key={index}
              className={`whitespace-pre-wrap tracking-wide animate-fadeIn flex items-center gap-1 transition-colors duration-300 ${getLogColor(log.type)}`}
            >
              {log.text}
              {log.text.includes("System idle.") && (
                <span className="w-1.5 h-3 bg-cyan-400 inline-block animate-pulse ml-1" />
              )}
            </div>
          ))}
          <div ref={consoleEndRef} />
        </div>

        {/* 우측: 메트릭 패널 */}
        <div className="hidden lg:flex flex-col gap-6 border-l border-slate-800/80 pl-5 text-xs text-slate-400 select-none w-64 shrink-0 justify-start font-mono">
          {/* 인프라 메트릭 */}
          <div>
            <div className="text-slate-500 font-extrabold mb-3 tracking-widest text-[11px] uppercase">
              ▼ System Metrics
            </div>
            <div className="space-y-2 text-slate-300">
              <div className="flex justify-between items-center hover:text-slate-200 transition-colors">
                <span>Cluster</span>
                <span className="font-medium">Harness-Swarm-01</span>
              </div>
              <div className="flex justify-between items-center hover:text-slate-200 transition-colors">
                <span>Engine</span>
                <span className="font-medium">v1.0.4-Beta</span>
              </div>
              <div className="flex justify-between items-center hover:text-slate-200 transition-colors">
                <span>Status</span>
                <span
                  className={`font-bold transition-all ${
                    revealedSteps.length > 0 && revealedSteps.length < 5
                      ? "animate-pulse"
                      : ""
                  }`}
                  style={{
                    color: revealedSteps.length > 0 && revealedSteps.length < 5
                      ? "var(--color-warning, #F59E0B)"
                      : "var(--color-brand, #00BAA4)"
                  }}
                >
                  {revealedSteps.length > 0 && revealedSteps.length < 5
                    ? "PROCESSING"
                    : revealedSteps.length === 5
                      ? "COMPLETED"
                      : "IDLE"}
                </span>
              </div>
            </div>
          </div>

          {/* 파이프라인 프로그레스 */}
          <div>
            <div className="text-slate-500 font-extrabold mb-3 tracking-widest text-[11px] uppercase">
              ▼ Pipeline Progress
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-slate-300 mb-1">
                <span>{pipelineProgress.completed}</span>
                <span className="text-slate-500">/ {pipelineProgress.total}</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500 ease-out"
                  style={{
                    width: `${pipelineProgress.percentage}%`,
                    background: "linear-gradient(to right, var(--color-brand, #00BAA4), var(--color-safe, #10B981))"
                  }}
                />
              </div>
            </div>
          </div>

          {/* 에이전트 상태 */}
          <div>
            <div className="text-slate-500 font-extrabold mb-3 tracking-widest text-[11px] uppercase">
              ▼ Swarm Status
            </div>
            <div className="space-y-2">
              {AGENT_ORDER.map((agent, i) => {
                const isActive = revealedSteps.length >= i + 1;
                const meta = AGENT_META[agent];
                const agentColor = `var(--color-${agent}, #00BAA4)`;

                return (
                  <div key={agent} className="flex justify-between items-center">
                    <span className="text-slate-400 font-mono text-[10px]">{meta.label}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-extrabold tracking-wide transition-all duration-300`}
                      style={{
                        backgroundColor: isActive ? `${agentColor}20` : "var(--color-slate-900, #0f172a)",
                        color: isActive ? agentColor : "var(--color-slate-600, #475569)"
                      }}
                    >
                      {isActive ? "ACTIVE" : "STANDBY"}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
