import { PIPELINE_STATUS_LABEL, type PipelineResult } from "../types";
import PrescriptionTable from "./PrescriptionTable";

interface Props {
  result: PipelineResult;
}

function SoapSection({ label, text }: { label: string; text: { ko: string; en: string } }) {
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2.5">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 whitespace-pre-wrap text-sm text-gray-800">{text.ko}</p>
      <p className="mt-1 whitespace-pre-wrap text-xs text-gray-400">{text.en}</p>
    </div>
  );
}

const STATUS_EXPLANATION: Record<string, string> = {
  unsupported_surgery: "입력된 수술명이 지원 범위(ACL 재건)에 해당하지 않아 즉시 종료했습니다.",
  manual_review_required: "동반 술식이 감지되어 규칙셋이 통째로 달라지므로, 자동 판정 대신 PT 수동 검토로 넘어갑니다.",
  insufficient_evidence: "이 조건에 맞는 운동을 지침 데이터에서 충분히 찾지 못해, 근거 없는 운동을 임의로 채우지 않고 중단했습니다.",
  red_flag: "안전 규칙 hard 위반이 11건 이상 감지되어 자동 처방을 중단했습니다. 즉시 담당 PT의 검토가 필요합니다.",
  failed: "자동 교정 한도 내에서 위반이 해소되지 않았거나 리포트 품질 검수를 통과하지 못했습니다.",
};

export default function ValidationReport({ result }: Props) {
  if (result.status === "red_flag") {
    return (
      <div className="rounded-2xl border-2 border-red-400 bg-red-50 p-6">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🚩</span>
          <h2 className="text-lg font-bold text-red-900">{PIPELINE_STATUS_LABEL.red_flag}</h2>
        </div>
        <p className="mt-3 text-sm text-red-800">{STATUS_EXPLANATION.red_flag}</p>
        {result.detail && (
          <p className="mt-2 rounded-md bg-red-100 px-3 py-1.5 text-xs font-mono text-red-700">
            상세: {result.detail}
          </p>
        )}
      </div>
    );
  }

  if (result.status !== "ready_for_reporter" || !result.report) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
        <h2 className="text-lg font-semibold text-amber-900">{PIPELINE_STATUS_LABEL[result.status]}</h2>
        <p className="mt-2 text-sm text-amber-800">
          {STATUS_EXPLANATION[result.status] ?? "파이프라인이 최종 리포트를 생성하지 못했습니다."}
        </p>
        {result.detail && <p className="mt-2 text-xs text-amber-600">상세: {result.detail}</p>}
      </div>
    );
  }

  const { reportMeta, soap, manualReview, safety } = result.report;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">검수 리포트 (SOAP)</h2>
          <p className="mt-1 text-sm text-gray-500">
            {reportMeta.phase} · 수술 후 {reportMeta.weekPostOp}주 · {reportMeta.recordId}
          </p>
          <p className="mt-0.5 text-xs text-gray-400">
            프로토콜 출처: {reportMeta.protocolSource.name}
            {reportMeta.protocolSource.refs.length > 0 && ` (${reportMeta.protocolSource.refs.join(", ")})`}
          </p>
        </div>
        <span
          className={
            "inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 " +
            (safety.finalGatePassed
              ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
              : "bg-red-50 text-red-700 ring-red-200")
          }
        >
          {safety.finalGatePassed ? "안전성 검증 통과" : "안전성 검증 실패"}
        </span>
      </div>

      {result.correctionUsed && (
        <div className="mt-4 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800 ring-1 ring-blue-200">
          <span className="font-semibold">자동 교정 발생:</span> 초안에서 규칙 위반이 감지되어 총{" "}
          {result.iterations}회 검증 끝에 통과했습니다.
        </div>
      )}

      <div className="mt-5 space-y-2">
        <SoapSection label="Subjective" text={soap.subjective} />
        <SoapSection label="Objective" text={soap.objective} />
        <SoapSection label="Assessment" text={soap.assessment} />
        <SoapSection label="Plan" text={{ ko: soap.plan.ko, en: soap.plan.en }} />
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-900">처방 운동 ({soap.plan.exercises.length}개)</h3>
        <div className="mt-3">
          <PrescriptionTable items={soap.plan.exercises} />
        </div>
      </div>

      {manualReview.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-gray-900">PT 수동 확인 필요</h3>
          <ul className="mt-3 space-y-1.5">
            {manualReview.map((item, i) => (
              <li key={i} className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 ring-1 ring-amber-200">
                <span className="font-semibold">{item.item}</span> — {item.note.ko}
                <div className="text-xs text-amber-600">{item.note.en}</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-6 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700 ring-1 ring-amber-200">
        ⚠ 본 화면은 Harness 시연을 위한 데모입니다(규칙표·운동 데이터가 SAMPLE). 실제 임상 처방에는 사용할 수 없습니다.
      </p>
    </div>
  );
}
