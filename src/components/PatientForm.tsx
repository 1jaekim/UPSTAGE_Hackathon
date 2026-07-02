import { useState } from "react";
import {
  GRAFT_LABEL,
  REHAB_PHASE_LABEL,
  REHAB_PHASE_ORDER,
  SURGERY_LABEL,
  type PatientInput,
  type RehabPhase,
} from "../types";

interface Props {
  disabled: boolean;
  onSubmit: (input: PatientInput) => void;
}

export default function PatientForm({ disabled, onSubmit }: Props) {
  const [phase, setPhase] = useState<RehabPhase>("PHASE_I");
  const [weekPostOp, setWeekPostOp] = useState(2);
  const [age, setAge] = useState(45);
  const [concomitantProcedure, setConcomitantProcedure] = useState("");
  const [painNrs, setPainNrs] = useState<string>("");
  const [swelling, setSwelling] = useState(false);
  const [notes, setNotes] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      surgeryType: "ACL_RECON",
      weekPostOp,
      age,
      concomitantProcedure: concomitantProcedure.trim() || null,
      painNrs: painNrs === "" ? null : Number(painNrs),
      swelling,
      notes,
      surgeryDetails: { phase, graftType: "hamstring_autograft" },
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm"
    >
      <h2 className="text-lg font-semibold text-gray-900">처방 입력</h2>
      <p className="mt-1 text-sm text-gray-500">
        회복 주차와 환자 정보를 입력하면 Harness가 단계별 운동 처방과 검수 리포트를 생성합니다.
      </p>

      <div className="mt-5 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">수술명</label>
          <div className="mt-1.5 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600">
            {SURGERY_LABEL.ACL_RECON}
            <span className="ml-2 text-xs text-gray-400">(현재 단일 지원 범위)</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">재활 단계 (Phase)</label>
          <select
            value={phase}
            onChange={(e) => setPhase(e.target.value as RehabPhase)}
            disabled={disabled}
            className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
          >
            {REHAB_PHASE_ORDER.map((p) => (
              <option key={p} value={p}>
                {REHAB_PHASE_LABEL[p]}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">회복 주차</label>
            <input
              type="number"
              min={0}
              max={16}
              value={weekPostOp}
              onChange={(e) => setWeekPostOp(Number(e.target.value))}
              disabled={disabled}
              className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">환자 나이</label>
            <input
              type="number"
              min={1}
              max={110}
              value={age}
              onChange={(e) => setAge(Number(e.target.value))}
              disabled={disabled}
              className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">이식건 종류</label>
          <div className="mt-1.5 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600">
            {GRAFT_LABEL.hamstring_autograft}
            <span className="ml-2 text-xs text-gray-400">(현재 단일 지원 범위)</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">동반 술식 (선택)</label>
          <input
            type="text"
            value={concomitantProcedure}
            onChange={(e) => setConcomitantProcedure(e.target.value)}
            disabled={disabled}
            placeholder="예: 반월판 봉합, 연골 손상 동반"
            className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">통증 수준 (NRS, 선택)</label>
            <input
              type="number"
              min={0}
              max={10}
              value={painNrs}
              onChange={(e) => setPainNrs(e.target.value)}
              disabled={disabled}
              placeholder="0~10"
              className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>
          <div className="flex items-end pb-2.5">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input
                type="checkbox"
                checked={swelling}
                onChange={(e) => setSwelling(e.target.checked)}
                disabled={disabled}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              부종 있음
            </label>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">특이사항 (선택)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={disabled}
            rows={2}
            placeholder="자유 텍스트로 입력. 위 구조화 필드 외의 특이사항을 적어주세요."
            className="mt-1.5 w-full resize-none rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={disabled}
        className="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
      >
        {disabled ? "파이프라인 실행 중..." : "처방 생성 및 안전성 검증 시작"}
      </button>
    </form>
  );
}
