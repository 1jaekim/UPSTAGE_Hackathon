import { useAnimationState } from "./hooks/useAnimationState";
import Header from "./components/Header";
import PatientForm from "./components/PatientForm";
import PipelineStepper from "./components/PipelineStepper";
import AgentConsole from "./components/feature/AgentConsole";
import SoapReport from "./components/feature/SoapReport";

export default function App() {
  const {
    isRunning,
    revealedSteps,
    currentPatient,
    showSoap,
    startPipeline
  } = useAnimationState();

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "var(--color-slate-50, #f8fafc)" }}>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <div 
          className="bg-white rounded-3xl shadow-2xl border border-slate-200/50 p-6 sm:p-8 lg:p-10 flex flex-col gap-8 hover:border-slate-300/50 transition-colors duration-500"
        >
          
          {/* 헤더 */}
          <div className="w-full">
            <Header />
          </div>
          
          {/* 메인 콘텐츠 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
            {/* 좌측: 입력 폼 (33%) */}
            <div className="lg:col-span-1">
              <PatientForm 
                disabled={isRunning} 
                onSubmit={startPipeline} 
              />
            </div>
            
            {/* 우측: 동적 패널 (67%) */}
            <div className="lg:col-span-2 relative w-full min-h-[560px] bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden flex flex-col">
              
              {/* 스크린 1: 파이프라인 스테퍼 */}
              <div 
                className={`absolute inset-0 transition-opacity duration-500 ease-in-out ${
                  showSoap ? "opacity-0 pointer-events-none" : "opacity-100"
                }`}
              >
                <div className="h-full overflow-y-auto scrollbar-thin">
                  <PipelineStepper 
                    revealedSteps={revealedSteps} 
                    isRunning={isRunning} 
                  />
                </div>
              </div>

              {/* 스크린 2: SOAP 리포트 */}
              <div 
                className={`absolute inset-0 transition-opacity duration-[1500ms] ease-out ${
                  showSoap ? "opacity-100 delay-[700ms]" : "opacity-0 pointer-events-none"
                }`}
              >
                {currentPatient && (
                  <div className="h-full">
                    <SoapReport patientData={currentPatient} />
                  </div>
                )}
              </div>

            </div>
          </div>

          {/* 하단: 콘솔 */}
          <div className="w-full shadow-lg rounded-2xl overflow-hidden mt-4">
            <AgentConsole revealedSteps={revealedSteps} />
          </div>

        </div>
      </main>
    </div>
  );
}
