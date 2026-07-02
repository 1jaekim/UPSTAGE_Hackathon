import { useState } from "react";
import { SURGERY_LABEL, type PatientInput, type SurgeryType } from "../types";

interface Props {
  disabled: boolean;
  onSubmit: (input: PatientInput) => void;
}

const SURGERY_TYPES: SurgeryType[] = ["ACL_RECON", "ROTATOR_CUFF", "TKA"];

const GRAFT_LABEL: Record<SurgeryType, string> = {
  ACL_RECON: "이식건 종류",
  ROTATOR_CUFF: "봉합 범위 / 특이사항",
  TKA: "보형물 종류 / 특이사항",
};

const GRAFT_PLACEHOLDER: Record<SurgeryType, string> = {
  ACL_RECON: "예: 자가건(BTB), 동종건",
  ROTATOR_CUFF: "예: 극상근 전층 파열 봉합",
  TKA: "예: 후방십자인대 보존형",
};

export default function PatientForm({ disabled, onSubmit }: Props) {
  const [surgeryType, setSurgeryType] = useState<SurgeryType>("ACL_RECON");
  const [recoveryWeek, setRecoveryWeek] = useState(2);
  const [age, setAge] = useState(45);
  const [graftType, setGraftType] = useState("");
  const [notes, setNotes] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({ surgeryType, recoveryWeek, age, graftType, notes });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm"
    >
      <h2 className="text-lg font-semibold text-gray-900">처방 입력</h2>
      <p className="mt-1 text-sm text-gray-500">
        수술명, 회복 주차, 환자 정보를 입력하면 Generator Agent가 단계별 운동 처방 초안을 생성합니다.
      </p>

      <div className="mt-5 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">수술명</label>
          <select
            value={surgeryType}
            onChange={(e) => setSurgeryType(e.target.value as SurgeryType)}
            disabled={disabled}
            className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
          >
            {SURGERY_TYPES.map((type) => (
              <option key={type} value={type}>
                {SURGERY_LABEL[type]}
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
              value={recoveryWeek}
              onChange={(e) => setRecoveryWeek(Number(e.target.value))}
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
          <label className="block text-sm font-medium text-gray-700">{GRAFT_LABEL[surgeryType]}</label>
          <input
            type="text"
            value={graftType}
            onChange={(e) => setGraftType(e.target.value)}
            disabled={disabled}
            placeholder={GRAFT_PLACEHOLDER[surgeryType]}
            className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">특이사항 (선택)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={disabled}
            rows={2}
            placeholder="예: 통증 VAS 3/10, 부종 경미"
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
