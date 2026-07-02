import { useState } from "react";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import type { PatientData } from "../types";

interface Props {
  disabled: boolean;
  onSubmit: (data: PatientData) => void;
}

interface FormErrors {
  week?: string;
  age?: string;
  surgery?: string;
}

export default function PatientForm({ disabled, onSubmit }: Props) {
  const [formData, setFormData] = useState<PatientData>({
    surgery: "전방십자인대(ACL) 재건술",
    week: "2",
    age: "45",
    graftType: "자가건(BTB), 동종건",
    notes: "통증 VAS 3/10, 부종 경미",
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validateField = (name: string, value: string): string | undefined => {
    if (name === "week") {
      const num = parseInt(value);
      if (isNaN(num) || num < 1 || num > 52) return "1-52주 범위 내 입력해주세요";
    }
    if (name === "age") {
      const num = parseInt(value);
      if (isNaN(num) || num < 18 || num > 120) return "18-120세 범위 내 입력해주세요";
    }
    if (name === "surgery" && !value) return "수술명을 선택해주세요";
    return undefined;
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    const error = validateField(name, value);
    setErrors((prev) => ({
      ...prev,
      [name]: error,
    }));
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
  };

  const isFormValid =
    formData.surgery &&
    formData.week &&
    formData.age &&
    !errors.surgery &&
    !errors.week &&
    !errors.age;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;
    onSubmit(formData);
  };

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm h-full flex flex-col transition-all duration-200">
      {/* 헤더 */}
      <div className="mb-6">
        <h2 className="text-lg font-bold text-slate-900">처방 입력</h2>
        <p className="text-xs text-slate-500 mt-1">
          환자 정보를 입력하면 Generator Agent가 맞춤형 운동 처방을 생성합니다.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col flex-1 gap-4">
        
        {/* 수술명 */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-slate-700">
            수술명 <span className="text-red-500">*</span>
          </label>
          <select
            name="surgery"
            value={formData.surgery}
            onChange={handleChange}
            onBlur={handleBlur}
            disabled={disabled}
            className={`w-full rounded-lg p-2.5 text-sm transition-all duration-200 ${
              touched.surgery && errors.surgery
                ? "border-2 border-red-500 bg-red-50/30 focus:ring-red-500/20"
                : "border border-slate-300 bg-white hover:border-slate-400 focus:border-brand focus:ring-1 focus:ring-brand/50"
            } focus:outline-none disabled:opacity-50 disabled:bg-slate-50`}
            style={
              touched.surgery && !errors.surgery
                ? { borderColor: "var(--color-safe, #10B981)" }
                : {}
            }
          >
            <option value="">수술명 선택...</option>
            <option value="전방십자인대(ACL) 재건술">전방십자인대(ACL) 재건술</option>
            <option value="L4-L5 척추 유합술">L4-L5 척추 유합술</option>
            <option value="미세현미경 디스크 제거술">미세현미경 디스크 제거술</option>
          </select>
          {touched.surgery && errors.surgery && (
            <div className="flex items-center gap-1.5 text-red-600 text-xs mt-1">
              <AlertCircle className="w-3.5 h-3.5" />
              {errors.surgery}
            </div>
          )}
        </div>

        {/* 회복 주차 + 나이 */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700">
              회복 주차 <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type="number"
                name="week"
                value={formData.week}
                onChange={handleChange}
                onBlur={handleBlur}
                disabled={disabled}
                min="1"
                max="52"
                className={`input-default w-full ${
                  touched.week && errors.week ? "input-error" : ""
                }`}
              />
              {!errors.week && touched.week && (
                <CheckCircle2 className="absolute right-3 top-3 w-4 h-4 text-green-500" />
              )}
            </div>
            {touched.week && errors.week && (
              <div className="text-red-600 text-xs flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                {errors.week}
              </div>
            )}
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700">
              환자 나이 <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type="number"
                name="age"
                value={formData.age}
                onChange={handleChange}
                onBlur={handleBlur}
                disabled={disabled}
                min="18"
                max="120"
                className={`input-default w-full ${
                  touched.age && errors.age ? "input-error" : ""
                }`}
              />
              {!errors.age && touched.age && (
                <CheckCircle2 className="absolute right-3 top-3 w-4 h-4 text-green-500" />
              )}
            </div>
            {touched.age && errors.age && (
              <div className="text-red-600 text-xs flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                {errors.age}
              </div>
            )}
          </div>
        </div>

        {/* 이식건 */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-slate-700">
            이식건 종류 <span className="text-slate-400">(선택)</span>
          </label>
          <input
            type="text"
            name="graftType"
            value={formData.graftType}
            onChange={handleChange}
            placeholder="예: 자가건(BTB), 동종건"
            disabled={disabled}
            className="input-default"
          />
        </div>

        {/* 특이사항 */}
        <div className="space-y-1.5 flex-1">
          <label className="block text-xs font-semibold text-slate-700">
            특이사항 <span className="text-slate-400">(선택)</span>
          </label>
          <textarea
            name="notes"
            value={formData.notes}
            onChange={handleChange}
            placeholder="예: 통증 VAS 3/10, 부종 경미"
            disabled={disabled}
            rows={3}
            className="input-default w-full resize-none"
          />
        </div>

        {/* CTA 버튼 */}
        <div className="pt-4 border-t border-slate-100">
          <button
            type="submit"
            disabled={disabled || !isFormValid}
            className="btn-primary w-full py-3"
            style={{
              background: disabled || !isFormValid 
                ? "var(--color-slate-300, #cbd5e1)"
                : "linear-gradient(to right, var(--color-brand, #00BAA4), var(--color-safe, #10B981))"
            }}
          >
            {disabled ? (
              <div className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                검증 진행 중...
              </div>
            ) : (
              "처방 생성 및 안전성 검증 시작"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
