import type { ReportExercise } from "../types";

interface Props {
  items: ReportExercise[];
}

export default function PrescriptionTable({ items }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">운동</th>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">세트/반복</th>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">빈도</th>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">강도</th>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">근거(Rationale)</th>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">출처</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {items.map((item, i) => (
            <tr key={i}>
              <td className="px-4 py-2.5 font-medium text-gray-900">
                {item.name.ko}
                <div className="text-xs font-normal text-gray-400">{item.name.en}</div>
              </td>
              <td className="px-4 py-2.5 text-gray-700">
                {item.sets}세트 × {item.reps}회
              </td>
              <td className="px-4 py-2.5 text-gray-700">
                {item.frequency.ko}
                <div className="text-xs text-gray-400">{item.frequency.en}</div>
              </td>
              <td className="px-4 py-2.5 text-gray-700">
                {item.intensity.ko}
                <div className="text-xs text-gray-400">{item.intensity.en}</div>
              </td>
              <td className="max-w-xs px-4 py-2.5 text-gray-500">
                {item.rationale.ko}
                <div className="text-xs text-gray-400">{item.rationale.en}</div>
              </td>
              <td className="px-4 py-2.5 text-xs text-gray-400">{item.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
