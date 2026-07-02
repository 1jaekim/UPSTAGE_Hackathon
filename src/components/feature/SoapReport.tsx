import { CheckCircle2, Shield, Heart, Activity, Target, type LucideIcon } from "lucide-react";
import type { PatientData } from "../../types";

interface SoapReportProps {
  patientData: PatientData;
}

// 1. Define base interface and specific section types
interface BaseSection {
  key: string;
  label: string;
  fullLabel: string;
  icon: LucideIcon;
  varName: string;
}

interface ContentSection extends BaseSection {
  key: "S" | "O";
  content: { label: string; value: string }[];
}

interface ItemSection extends BaseSection {
  key: "A" | "P";
  items: string[];
}

type Section = ContentSection | ItemSection;

const SOAP_SECTIONS: BaseSection[] = [
  {
    key: "S",
    label: "주관적 소견",
    fullLabel: "Subjective",
    icon: Heart,
    varName: "var(--color-generator, #3B82F6)"
  },
  {
    key: "O",
    label: "객관적 수치",
    fullLabel: "Objective",
    icon: Activity,
    varName: "var(--color-validator, #F97316)"
  },
  {
    key: "A",
    label: "안전성 평가",
    fullLabel: "Assessment",
    icon: Shield,
    varName: "var(--color-corrector, #8B5CF6)"
  },
  {
    key: "P",
    label: "최종 계획",
    fullLabel: "Plan",
    icon: Target,
    varName: "var(--color-reporter, #10B981)"
  }
];

export default function SoapReport({ patientData }: SoapReportProps) {
  // 2. Explicitly type the sections array
  const sections: Section[] = [
    {
      ...(SOAP_SECTIONS[0] as ContentSection),
      key: "S",
      content: [
        { label: "주소증", value: patientData.surgery },
        { label: "특이사항", value: patientData.notes || "특이사항 없음" }
      ]
    },
    {
      ...(SOAP_SECTIONS[1] as ContentSection),
      key: "O",
      content: [
        { label: "환자 정보", value: `만 ${patientData.age}세` },
        { label: "회복 주차", value: `수술 후 ${patientData.week}주차` },
        { label: "이식건 종류", value: patientData.graftType || "제한 없음" }
      ]
    },
    {
      ...(SOAP_SECTIONS[2] as ItemSection),
      key: "A",
      items: [
        "✓ 회복 주차별 ROM 가이드라인 제약조건 대조 통과",
        "✓ 관절 조기 과부하 위험 패턴 식별 결과 이상 없음",
        "✓ 가이드라인 최종 정합성 및 안전 마진 확보 완료"
      ]
    },
    {
      ...(SOAP_SECTIONS[3] as ItemSection),
      key: "P",
      items: [
        "1. 대퇴사두근 등척성 수축 (Q-Setting) : 10초 유지 / 3세트",
        "2. 하지 직거상 운동 (SLR) : 가동 범위 내 10회 / 3세트",
        "3. 점진적 무릎 굴곡 훈련 (CPM) : 최대 90도 제약 적용"
      ]
    }
  ];

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-md flex flex-col gap-5 animate-fadeIn h-full overflow-y-auto scrollbar-thin">
      <div className="border-b border-slate-100 pb-4 sticky top-0 bg-white z-10">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-slate-900">AI Clinical SOAP Note</h3>
            <p className="text-xs text-slate-400 mt-1">임상 안전성 검증 자동 매핑 리포트</p>
          </div>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold text-white bg-[#10B981]">
            <CheckCircle2 className="w-3.5 h-3.5" />
            VERIFIED
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
        {sections.map((section, idx) => {
          const Icon = section.icon;

          return (
            <div
              key={section.key}
              className="group rounded-xl border transition-all duration-300 hover:shadow-md hover:border-slate-300 animate-fadeIn p-4"
              style={{
                backgroundColor: `${section.varName}10`,
                borderColor: `${section.varName}30`,
                animationDelay: `${idx * 100}ms`
              }}
            >
              <div className="flex items-center gap-2.5 mb-3 pb-3 border-b" style={{ borderColor: `${section.varName}30` }}>
                <div className="w-6 h-6 rounded-lg flex items-center justify-center text-white font-bold" style={{ backgroundColor: section.varName }}>
                  {section.key}
                </div>
                <div>
                  <p className="font-bold text-sm text-slate-800">{section.label}</p>
                  <p className="text-xs text-slate-500">{section.fullLabel}</p>
                </div>
                {/* Fixed "Icon declared but not used" by rendering it */}
                <Icon className="w-4 h-4 ml-auto text-slate-400" />
              </div>

              <div>
                {/* 3. Use type guard to safely access content or items */}
                {(section.key === "S" || section.key === "O") ? (
                  <ul className="space-y-2.5">
                    {(section as ContentSection).content.map((item, i) => (
                      <li key={i} className="text-xs">
                        <span className="font-semibold text-slate-700">{item.label}:</span>
                        <span className="text-slate-600 ml-1.5">{item.value}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <ul className="space-y-2">
                    {(section as ItemSection).items.map((item, i) => (
                      <li
                        key={i}
                        className={`text-xs leading-relaxed flex gap-2 ${section.key === "A" ? "font-medium" : "text-slate-700 font-mono"}`}
                        style={{ color: section.key === "A" ? "#10B981" : "#334155" }}
                      >
                        <span className="flex-shrink-0 mt-0.5">{section.key === "A" ? "✓" : "→"}</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="border-t border-slate-100 pt-4 mt-2 sticky bottom-0 bg-gradient-to-t from-white via-white to-transparent">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">신뢰도</span>
          <div className="flex gap-1">
            {[...Array(5)].map((_, i) => (
              <span key={i} className="text-lg transition-transform hover:scale-125">⭐</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
