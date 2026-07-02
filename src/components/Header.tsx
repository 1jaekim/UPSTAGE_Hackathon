export default function Header() {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto max-w-6xl px-6 py-6">
        <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 ring-1 ring-blue-200">
          Harness Engineering
        </span>
        <h1 className="mt-3 text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
          운동 처방 안전성 검증 에이전트
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-gray-500 sm:text-base">
          수술 후 재활 운동처방을 AI가 생성하고, 스스로 안전성을 검사해 금기·범위 위반을 자동으로 고친 뒤 근거가
          담긴 검수 리포트를 내보내는 Harness
        </p>
      </div>
    </header>
  );
}
