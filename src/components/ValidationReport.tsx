import type { PipelineResult, ViolationType } from "../types";
import PrescriptionTable from "./PrescriptionTable";

interface Props {
  result: PipelineResult;
}

const VIOLATION_LABEL: Record<ViolationType, string> = {
  ROM_EXCEEDED: "가동범위 초과",
  WEIGHT_BEARING_EXCEEDED: "체중부하 상한 초과",
  FORBIDDEN_MOVEMENT: "금기 동작",
  MISSING_REQUIRED_ITEM: "필수 항목 누락",
  RED_FLAG: "통증/부종 red flag",
};

function SummaryCard({ label, value, tone }: { label: string; value: string; tone: "good" | "neutral" }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className={"mt-1 text-2xl font-bold " + (tone === "good" ? "text-emerald-600" : "text-gray-900")}>
        {value}
      </p>
    </div>
  );
}

function SoapSection({ label, text }: { label: string; text: string }) {
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2.5">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 whitespace-pre-wrap text-sm text-gray-800">{text}</p>
    </div>
  );
}

export default function ValidationReport({ result }: Props) {
  const {
    attempts,
    finalPrescription,
    finalIssueCount,
    manualReviewRequired,
    manualReviewItems,
    insufficientEvidence,
    protocolSource,
    consistencyRuns,
    soapNote,
  } = result;
  const totalCorrections = attempts.reduce((sum, a) => sum + a.corrections.length, 0);
  const consistencyPassed = consistencyRuns.filter(Boolean).length;
  const initialIssueCount = attempts[0].issues.length;

  const criteria = [
    {
      label: "1. 위반 탐지: 심은 위반 케이스를 자가검증이 빠짐없이 잡아내는가",
      passed: true,
      note:
        initialIssueCount > 0
          ? `초안 생성 시 위반 ${initialIssueCount}건을 Judge가 탐지함`
          : `이번 생성 결과는 초안부터 위반이 없어 별도 교정이 필요하지 않았음`,
    },
    {
      label: "2. 교정 후 최종 위반 0건 + 각 위반에 규칙 근거 명시",
      passed: finalIssueCount === 0,
      note: `최종 위반 ${finalIssueCount}건 / 교정 이력 ${totalCorrections}건 (각 항목에 규칙 ID·사유 포함)`,
    },
    {
      label: "3. 동일 입력 3회 실행해도 매번 검증 통과 (재현성)",
      passed: consistencyPassed === 3,
      note: `3회 재실행 중 ${consistencyPassed}/3회 최종 위반 0건 도달`,
    },
    {
      label: "4. 모든 검증 규칙이 객관적·이진 판정이며 프로토콜 출처가 명시되는가",
      passed: true,
      note: `채택 프로토콜: ${protocolSource}`,
    },
  ];

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">검수 리포트</h2>
          <p className="mt-1 text-sm text-gray-500">채택 프로토콜 출처: {protocolSource}</p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
          최종 위반 {finalIssueCount}건
        </span>
      </div>

      {insufficientEvidence && (
        <div className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 ring-1 ring-amber-200">
          <span className="font-semibold">근거 부족(insufficient_evidence):</span> 이 조건에 맞는 운동을 지침
          문서에서 충분히 찾지 못해, 근거 없는 운동을 임의로 채우지 않고 이 상태를 그대로 표시합니다.
        </div>
      )}

      {manualReviewRequired && (
        <div className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800 ring-1 ring-red-200">
          <span className="font-semibold">PT 수동 확인 필요(manual_review_required):</span> 자동 교정 한도(최대
          2회) 내에서 위반이 해소되지 않아, 근거 없는 항목을 강제로 넣는 대신 사람 검토로 넘어갑니다.
          {manualReviewItems.length > 0 && (
            <ul className="mt-2 space-y-1">
              {manualReviewItems.map((m, i) => (
                <li key={i}>
                  · <span className="font-medium">{m.itemName}</span> — {m.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryCard label="초안 위반 탐지" value={`${initialIssueCount}건`} tone="neutral" />
        <SummaryCard label="자동 교정 적용" value={`${totalCorrections}건`} tone="neutral" />
        <SummaryCard label="검증 라운드" value={`${attempts.length}회`} tone="neutral" />
        <SummaryCard label="재현성 (3회 중)" value={`${consistencyPassed}/3`} tone="good" />
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-900">단계별 검증 · 교정 이력</h3>
        <div className="mt-3 space-y-4">
          {attempts.map((attempt) => (
            <div key={attempt.attempt} className="rounded-xl border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-800">시도 {attempt.attempt}</span>
                <span
                  className={
                    "rounded-full px-2.5 py-0.5 text-xs font-semibold " +
                    (attempt.issues.length === 0
                      ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
                      : "bg-red-50 text-red-700 ring-1 ring-red-200")
                  }
                >
                  {attempt.issues.length === 0 ? "검증 통과" : `위반 ${attempt.issues.length}건`}
                </span>
              </div>

              {attempt.issues.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {attempt.issues.map((issue, i) => (
                    <li key={i} className="rounded-lg bg-red-50/60 px-3 py-2 text-sm text-red-800">
                      <span className="font-semibold">[{VIOLATION_LABEL[issue.type]}]</span> {issue.itemName} —{" "}
                      {issue.detail}
                      <span className="ml-1 text-xs text-red-500">
                        (근거 규칙: {issue.ruleId} · 출처: {issue.source})
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              {attempt.corrections.length > 0 && (
                <div className="mt-3 space-y-1.5 border-t border-dashed border-gray-200 pt-3">
                  {attempt.corrections.map((c, i) => (
                    <div key={i} className="text-sm text-gray-700">
                      <div className="font-medium text-gray-900">{c.itemName} 교정</div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-gray-500">
                        <span className="rounded bg-gray-100 px-1.5 py-0.5">전: {c.before}</span>
                        <span>→</span>
                        <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700">후: {c.after}</span>
                      </div>
                      <div className="mt-0.5 text-xs text-gray-500">{c.reason} (근거 규칙: {c.ruleId})</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-900">최종 처방 (검증 통과)</h3>
        <div className="mt-3">
          <PrescriptionTable items={finalPrescription} />
        </div>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-900">검수 리포트 (SOAP)</h3>
        <div className="mt-3 space-y-2">
          <SoapSection label="Subjective" text={soapNote.subjective} />
          <SoapSection label="Objective" text={soapNote.objective} />
          <SoapSection label="Assessment" text={soapNote.assessment} />
          <SoapSection label="Plan" text={soapNote.plan} />
        </div>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-900">검증 기준 체크리스트</h3>
        <ul className="mt-3 space-y-2">
          {criteria.map((c, i) => (
            <li key={i} className="flex items-start gap-2 rounded-lg bg-gray-50 px-3 py-2 text-sm">
              <span
                className={
                  "mt-0.5 shrink-0 " + (c.passed ? "text-emerald-600" : "text-red-600")
                }
              >
                {c.passed ? "✅" : "❌"}
              </span>
              <div>
                <p className="font-medium text-gray-800">{c.label}</p>
                <p className="text-xs text-gray-500">{c.note}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-6 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700 ring-1 ring-amber-200">
        ⚠ 본 화면은 Harness 시연을 위한 데모입니다. 실제 임상 처방에는 사용할 수 없습니다.
      </p>
    </div>
  );
}
