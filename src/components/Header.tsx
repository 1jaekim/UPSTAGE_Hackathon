import { Zap } from "lucide-react";

export default function Header() {
  return (
    <header className="bg-transparent w-full flex flex-col items-start text-left gap-2">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
          운동 처방 안전성 검증 시스템
        </h1>
        <span 
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-widest hover:ring-1 transition-all duration-300"
          style={{
            backgroundColor: "var(--color-brand-dark, rgb(30, 41, 59))/5",
            color: "var(--color-brand, #00BAA4)",
            "--tw-ring-color": "var(--color-brand, #00BAA4)/30"
          } as React.CSSProperties}
        >
          <Zap className="w-3.5 h-3.5" />
          Harness v1.0
        </span>
      </div>

      <p className="text-sm text-slate-600 font-medium max-w-4xl leading-relaxed">
        멀티 에이전트 협업 기반 재활 프로토콜 생성 및 실시간 임상 가이드라인 교차 검증 솔루션
      </p>
    </header>
  );
}
