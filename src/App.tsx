import { useState } from "react";
import Header from "./components/Header";
import PatientForm from "./components/PatientForm";
import PipelineStepper from "./components/PipelineStepper";
import AgentConsole from "./components/feature/AgentConsole";
import SoapReport from "./components/feature/SoapReport"; // 💡 신규 파일 임포트

export default function App() {
  const [isRunning, setIsRunning] = useState(false);
  const [revealedSteps, setRevealedSteps] = useState<any[]>([]); 
  const [currentPatient, setCurrentPatient] = useState<any>(null); // 💡 환자 데이터 상태 추가

  const handleFormSubmit = (data: any) => {
    setCurrentPatient(data); // 💡 제출 데이터 동기화
    setIsRunning(true);
    setRevealedSteps([]); 

    // 0초: 오케스트레이터 가동
    setTimeout(() => {
      setRevealedSteps([
        { agent: "orchestrator", label: "환자 재활 안전성 검증 파이프라인 스케줄링 및 리소스 할당 완료", attempt: 1 }
      ]);
    }, 0);

    // 1.5초: 제너레이터 가동
    setTimeout(() => {
      setRevealedSteps((prev) => [
        ...prev,
        { agent: "generator", label: `${data.surgery} 기반 맞춤형 재활 운동 프로토콜 초안 설계 완료` }
      ]);
    }, 1500);

    // 3.0초: 밸리데이터 가동
    setTimeout(() => {
      setRevealedSteps((prev) => [
        ...prev,
        { agent: "validator", label: `회복 주차(${data.week}주) 대비 운동 강도 및 관절 가동 범위(ROM) 금기 요소 교차 검증 통과` }
      ]);
    }, 3000);

    // 4.5초: 콜렉터 가동
    setTimeout(() => {
      setRevealedSteps((prev) => [
        ...prev,
        { agent: "corrector", label: "미세 조정 및 임상적 안전성 최종 보정 완료 (위반 사항 없음)" }
      ]);
    }, 4500);

    // 6.0초: 리포터 가동 및 종료
    setTimeout(() => {
      setRevealedSteps((prev) => [
        ...prev,
        { agent: "reporter", label: "의학적 근거 중심의 안전성 검증 리포트 추출 완료" }
      ]);
      setIsRunning(false);
    }, 6000);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#CBD5E1]">
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-slate-50 rounded-[32px] shadow-2xl border border-slate-200/80 p-8 md:p-10 flex flex-col gap-8">
          
          <div className="w-full">
            <Header />
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
            <div className="lg:col-span-1 flex flex-col">
              <PatientForm disabled={isRunning} onSubmit={handleFormSubmit} />
            </div>
            
            {/* 💡 우측 컴포넌트: 파이프라인 스텝과 SOAP 리포트가 한 묶음으로 정렬선을 공유합니다 */}
            <div className="lg:col-span-2 flex flex-col gap-6">
              <PipelineStepper revealedSteps={revealedSteps} isRunning={isRunning} />
              
              {/* 🎯 5개 에이전트 연산이 끝나 마무리가 완료되면 실시간 데이터가 결합된 SOAP Note 노출 */}
              {revealedSteps.length === 5 && currentPatient && (
                <SoapReport patientData={currentPatient} />
              )}
            </div>
          </div>

          <div className="w-full shadow-lg rounded-2xl overflow-hidden">
            <AgentConsole revealedSteps={revealedSteps} />
          </div>

        </div>
      </main>
    </div>
  );
}