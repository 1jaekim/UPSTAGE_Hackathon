import { LOAD_LABEL, type PrescriptionItem } from "../types";

interface Props {
  items: PrescriptionItem[];
}

export default function PrescriptionTable({ items }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">운동</th>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">설명</th>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">가동범위</th>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">부하 단계</th>
            <th className="px-4 py-2.5 text-left font-semibold text-gray-600">세트/반복</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {items.map((item) => (
            <tr key={item.id}>
              <td className="px-4 py-2.5 font-medium text-gray-900">{item.name}</td>
              <td className="max-w-xs px-4 py-2.5 text-gray-500">{item.description}</td>
              <td className="px-4 py-2.5 text-gray-700">
                {item.romMin}~{item.romMax}°
              </td>
              <td className="px-4 py-2.5 text-gray-700">{LOAD_LABEL[item.loadLevel]}</td>
              <td className="px-4 py-2.5 text-gray-700">{item.setsReps}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
