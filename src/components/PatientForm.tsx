import React, { useState } from "react";

interface Props {
  disabled: boolean;
  onSubmit: (data: any) => void;
}

export default function PatientForm({ disabled, onSubmit }: Props) {
  const [surgery, setSurgery] = useState("전방십자인대(ACL) 재건술");
  const [week, setWeek] = useState("2");
  const [age, setAge] = useState("45");
  const [graftType, setGraftType] = useState("");
  const [notes, setNotes] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ surgery, week, age, graftType, notes });
  };

  return (
    <form 
      onSubmit={handleSubmit}
      className="rounded-2xl border border-slate-100 bg-white p-6 shadow-md h-full flex flex-col justify-between gap-5 animate-fadeIn"
    >
      <div className="flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">처방 입력</h2>
          <p className="text-xs text-gray-500 mt-1 leading-relaxed">
            수술명, 회복 주차, 환자 정보를 입력하면 Generator Agent가 단계별 운동 처방 초안을 생성합니다.
          </p>
        </div>

        {/* 수술명 선택 */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-gray-700">수술명</label>
          <select
            value={surgery}
            onChange={(e) => setSurgery(e.target.value)}
            disabled={disabled}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:border-[#00BAA4] focus:outline-none disabled:bg-gray-50 transition-colors"
          >
            <option>전방십자인대(ACL) 재건술</option>
            <option>반월상연골 봉합술</option>
            <option>인공관절 치환술</option>
          </select>
        </div>

        {/* 회복 주차 및 환자 나이 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-gray-700">회복 주차</label>
            <input
              type="number"
              value={week}
              onChange={(e) => setWeek(e.target.value)}
              disabled={disabled}
              placeholder="예: 2"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#00BAA4] focus:outline-none disabled:bg-gray-50 transition-colors"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-gray-700">환자 나이</label>
            <input
              type="number"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              disabled={disabled}
              placeholder="예: 45"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#00BAA4] focus:outline-none disabled:bg-gray-50 transition-colors"
            />
          </div>
        </div>

        {/* 이식건 종류 */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-gray-700">이식건 종류</label>
          <input
            type="text"
            value={graftType}
            onChange={(e) => setGraftType(e.target.value)}
            disabled={disabled}
            placeholder="예: 자가건(BTB), 동종건"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#00BAA4] focus:outline-none disabled:bg-gray-50 transition-colors"
          />
        </div>

        {/* 특이사항 */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-gray-700">특이사항 (선택)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={disabled}
            rows={3}
            placeholder="예: 통증 VAS 3/10, 부종 경미"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-[#00BAA4] focus:outline-none resize-none disabled:bg-gray-50 transition-colors"
          />
        </div>
      </div>

      {/* 버튼 색상 브랜드 민트칼라(#00BAA4) 고도화 */}
      <button
        type="submit"
        disabled={disabled}
        className={
          "w-full rounded-xl py-3 text-sm font-semibold text-white transition-all shadow-sm " +
          (disabled
            ? "bg-slate-300 cursor-not-allowed"
            : "bg-[#00BAA4] hover:bg-[#00A38F] active:scale-[0.99] shadow-md shadow-[#00BAA4]/10")
        }
      >
        {disabled ? "파이프라인 실행 중..." : "처방 생성 및 안전성 검증 시작"}
      </button>
    </form>
  );
}