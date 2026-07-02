export default function Header() {
  return (
    // 💡 items-start, text-left로 하단 대시보드 카드들의 좌측 끝선과 완벽히 축을 일치시킵니다.
    <header className="bg-transparent w-full flex flex-col items-start text-left gap-1.5">
      
      {/* 제목 + 가독성이 확보된 고대비 버전 배지 라인 */}
      <div className="flex items-center gap-2.5">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
          운동 처방 안전성 검증 시스템
        </h1>
        {/* 💡 프로젝터 화면에서도 뚜렷하게 보이도록 다크 민트 텍스트와 링 대비를 강화했습니다 */}
        <span className="inline-flex items-center rounded-md bg-[#00BAA4]/15 px-2 py-0.5 text-[10px] font-bold text-[#007A6B] ring-1 ring-[#00BAA4]/30 uppercase tracking-wider">
          Harness Engine v1.0
        </span>
      </div>

      {/* 하단 그리드 라인을 따라 시원하게 읽히는 전문 슬로건 */}
      <p className="text-xs sm:text-sm text-slate-500 font-medium tracking-tight max-w-3xl leading-relaxed">
        멀티 에이전트 협업 기반 재활 프로토콜 생성 및 실시간 임상 가이드라인 교차 검증 솔루션
      </p>

    </header>
  );
}