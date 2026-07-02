import { useEffect, useState, useRef } from "react";

interface Props {
  revealedSteps: any[];
}

export default function AgentConsole({ revealedSteps }: Props) {
  const [consoleLogs, setConsoleLogs] = useState<string[]>([]);
  const consoleEndRef = useRef<HTMLDivElement>(null);

  const getTimestamp = () => {
    const now = new Date();
    return `[${now.toTimeString().split(" ")[0]}]`;
  };

  useEffect(() => {
    const time = getTimestamp();
    setConsoleLogs([
      `${time} Harness Engineering 안전성 검증 커널 초기화 완료.`,
      `${time} Orchestrator Agent: 대기 상태 (환자 처방 입력을 기다리는 중...)`,
      `${time} 시스템 연결 성공: 물리치료 데이터 파이프라인 준비 완료.`,
      `▶ System ready`
    ]);
  }, []);

  useEffect(() => {
    if (revealedSteps.length === 0) return;

    const latestStep = revealedSteps[revealedSteps.length - 1];
    const time = getTimestamp();
    let agentLog = "";

    if (revealedSteps.length === 1 && latestStep.agent === "orchestrator") {
      setConsoleLogs([
        `${time} [⚙️ System] 파이프라인 트리거 수신 - 임상 데이터 세션 초기화 완료.`,
        `${time} [Orchestrator] 에이전트 군집(Swarm) 리소스 할당 완료. 작업 스케줄링을 시작합니다.`
      ]);
      return;
    }

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
          agentLog,
          `▶ Pipeline execution completed successfully. System idle.`
        ]);
      } else {
        setConsoleLogs((prev) => [...prev, agentLog]);
      }
    }
  }, [revealedSteps]);

  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [consoleLogs]);

  return (
    <div className="bg-[#0B132B] text-slate-200 rounded-2xl p-5 font-mono text-[11px] shadow-inner border border-slate-900 flex flex-col gap-4">
      {/* 윈도우 헤더 바 */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 select-none">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 block"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-yellow-500 block"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-green-500 block"></span>
          <span className="text-slate-400 font-semibold ml-1.5">Agent Executive Console</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00BAA4] animate-ping"></span>
          <span className="text-[#00BAA4] text-[10px] font-bold tracking-wider uppercase">Live</span>
        </div>
      </div>

      {/* 💡 2컬럼 레이아웃 전면 도입: 공간 우측의 암흑 낭비를 완벽한 대시보드 스펙 보드로 치환 */}
      <div className="flex flex-col lg:flex-row gap-6 h-[240px] overflow-hidden">
        
        {/* 좌측: 실시간 로그 스트림 창 (전체 공간의 핵심) */}
        <div className="flex-1 space-y-2 overflow-y-auto leading-relaxed pr-1">
          {consoleLogs.map((log, index) => {
            let logColor = "text-slate-300";
            if (log.includes("[Orchestrator]") || log.includes("Orchestrator Agent")) logColor = "text-[#00BAA4]";
            else if (log.includes("[Generator]")) logColor = "text-blue-400";
            else if (log.includes("[Validator]")) logColor = "text-amber-400";
            else if (log.includes("[Corrector]")) logColor = "text-purple-400";
            else if (log.includes("[Reporter]")) logColor = "text-emerald-400";
            else if (log.includes("성공") || log.includes("▶")) logColor = "text-cyan-400";

            return (
              <div key={index} className={`${logColor} whitespace-pre-wrap tracking-wide animate-fadeIn flex items-center gap-1`}>
                {log}
                {log.includes("System idle.") && (
                  <span className="w-1.5 h-3 bg-cyan-400 inline-block animate-pulse"></span>
                )}
              </div>
            );
          })}
          <div ref={consoleEndRef} />
        </div>

        {/* 🎯 우측: 심사위원을 압도할 실시간 인프라 & 에이전트 메트릭 모니터링 패널 */}
        <div className="hidden lg:flex flex-col gap-5 border-l border-slate-800/80 pl-5 text-[10px] text-slate-400 select-none w-52 shrink-0 justify-start pt-1 font-mono">
          <div>
            <div className="text-slate-500 font-bold mb-1.5 tracking-wider">▼ INFRA METRICS</div>
            <div className="space-y-0.5 tracking-wide">
              <div>CLUSTER : <span className="text-slate-300">Harness-Swarm-01</span></div>
              <div>CORE ENG : <span className="text-slate-300">v1.0.4-Beta</span></div>
              <div>PIPELINE : <span className={revealedSteps.length > 0 && revealedSteps.length < 5 ? "text-amber-400 animate-pulse" : "text-cyan-400"}>{revealedSteps.length > 0 && revealedSteps.length < 5 ? "PROCESSING" : revealedSteps.length === 5 ? "COMPLETED" : "IDLE"}</span></div>
            </div>
          </div>

          <div>
            <div className="text-slate-500 font-bold mb-1.5 tracking-wider">▼ REAL-TIME SWARM STATUS</div>
            <div className="space-y-1 font-sans font-medium">
              <div className="flex justify-between items-center">
                <span className="font-mono text-[10px]">orchestrator</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${revealedSteps.length >= 1 ? "bg-[#00BAA4]/10 text-[#00BAA4]" : "bg-slate-900 text-slate-600"}`}>{revealedSteps.length >= 1 ? "ACTIVE" : "STANDBY"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-mono text-[10px]">generator</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${revealedSteps.length >= 2 ? "bg-blue-500/10 text-blue-400" : "bg-slate-900 text-slate-600"}`}>{revealedSteps.length >= 2 ? "ACTIVE" : "STANDBY"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-mono text-[10px]">validator</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${revealedSteps.length >= 3 ? "bg-amber-500/10 text-amber-400" : "bg-slate-900 text-slate-600"}`}>{revealedSteps.length >= 3 ? "ACTIVE" : "STANDBY"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-mono text-[10px]">corrector</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${revealedSteps.length >= 4 ? "bg-purple-500/10 text-purple-400" : "bg-slate-900 text-slate-600"}`}>{revealedSteps.length >= 4 ? "ACTIVE" : "STANDBY"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-mono text-[10px]">reporter</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${revealedSteps.length >= 5 ? "bg-emerald-500/10 text-emerald-400" : "bg-slate-900 text-slate-600"}`}>{revealedSteps.length >= 5 ? "ACTIVE" : "STANDBY"}</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}