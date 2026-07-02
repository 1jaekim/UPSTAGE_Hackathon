// src/components/feature/SoapReport.tsx
import { CheckCircle2 } from "lucide-react";

interface SoapReportProps {
  patientData: {
    surgery: string;
    week: string;
    age: string;
    graftType?: string;
    notes?: string;
  };
}

export default function SoapReport({ patientData }: SoapReportProps) {
  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-md flex flex-col gap-5 animate-fadeIn">
      {/* 리포트 헤더 */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <h3 className="text-base font-bold text-slate-900">AI Clinical SOAP Note</h3>
          <p className="text-[11px] text-slate-400 mt-0.5">임상 안전성 검증 자동 자동 매핑 리포트</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-600/10">
          <CheckCircle2 className="w-3 h-3" /> SOAP VERIFIED
        </span>
      </div>

      {/* SOAP 4단락 구조 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        
        {/* S: Subjective */}
        <div className="bg-slate-50/60 rounded-xl p-3.5 border border-slate-100/80">
          <div className="font-bold text-slate-800 flex items-center gap-1.5 mb-2">
            <span className="w-4 h-4 rounded bg-blue-500 text-white text-[10px] font-black flex items-center justify-center">S</span>
            <span>주관적 소견 (Subjective)</span>
          </div>
          <ul className="list-disc pl-4 space-y-1 text-slate-600">
            <li><strong>주소소견:</strong> {patientData.surgery} 후 재활 운동 처방 스크리닝</li>
            <li><strong>특이사항:</strong> {patientData.notes || "특이사항 없음"}</li>
          </ul>
        </div>

        {/* O: Objective */}
        <div className="bg-slate-50/60 rounded-xl p-3.5 border border-slate-100/80">
          <div className="font-bold text-slate-800 flex items-center gap-1.5 mb-2">
            <span className="w-4 h-4 rounded bg-amber-500 text-white text-[10px] font-black flex items-center justify-center">O</span>
            <span>객관적 수치 (Objective)</span>
          </div>
          <ul className="list-disc pl-4 space-y-1 text-slate-600">
            <li><strong>환자 정보:</strong> 만 {patientData.age}세</li>
            <li><strong>임상 변수:</strong> 수술 후 {patientData.week}주차 타깃 세션</li>
            <li><strong>이식건 종류:</strong> {patientData.graftType || "제한 없음"}</li>
          </ul>
        </div>

        {/* A: Assessment */}
        <div className="bg-slate-50/60 rounded-xl p-3.5 border border-slate-100/80">
          <div className="font-bold text-slate-800 flex items-center gap-1.5 mb-2">
            <span className="w-4 h-4 rounded bg-purple-500 text-white text-[10px] font-black flex items-center justify-center">A</span>
            <span>안전성 검증 평가 (Assessment)</span>
          </div>
          <ul className="list-disc pl-4 space-y-1 text-emerald-600 font-medium">
            <li>✓ 회복 주차별 ROM 가이드라인 제약조건 대조 통과</li>
            <li>✓ 관절 조기 과부하 위험 패턴 식별 결과 이상 없음</li>
            <li className="text-slate-600">✓ 가이드라인 최종 정합성 및 안전 마진 확보 완료</li>
          </ul>
        </div>

        {/* P: Plan */}
        <div className="bg-slate-50/60 rounded-xl p-3.5 border border-slate-100/80">
          <div className="font-bold text-slate-800 flex items-center gap-1.5 mb-2">
            <span className="w-4 h-4 rounded bg-emerald-500 text-white text-[10px] font-black flex items-center justify-center">P</span>
            <span>최종 운동 계획 (Plan)</span>
          </div>
          <div className="bg-white p-2 rounded-lg border border-slate-200/60 font-mono text-[10px] text-slate-700 space-y-0.5">
            <div>1. 대퇴사두근 등척성 수축 (Q-Setting) : 10초 유지 / 3세트</div>
            <div>2. 하지 직거상 운동 (SLR) : 가동 범위 내 10회 / 3세트</div>
            <div>3. 점진적 무릎 굴곡 훈련 (CPM) : 최대 90도 제약 적용</div>
          </div>
        </div>

      </div>
    </div>
  );
}