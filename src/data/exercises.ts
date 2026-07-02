import type { ExerciseSpec, SurgeryType } from "../types";

// 데모용 운동 라이브러리. safe 항목은 규칙을 통과하도록, risky 항목은
// 특정 단계에서 규칙 위반이 발생하도록 의도적으로 설계되어 자가검증/자동교정 시연에 사용됩니다.
export const EXERCISE_LIBRARY: Record<SurgeryType, ExerciseSpec[]> = {
  ACL_RECON: [
    { id: "acl-quad-iso", name: "대퇴사두근 등척성 운동", description: "무릎을 편 상태로 대퇴사두근에 힘을 주어 5초 유지", romMin: 0, romMax: 10, loadLevel: "none", movementTag: "quad_isometric" },
    { id: "acl-heel-slide", name: "힐 슬라이드 (수동 ROM)", description: "누운 자세에서 발뒤꿈치를 엉덩이 쪽으로 미끄러뜨려 굴곡 각도 확보", romMin: 0, romMax: 90, loadLevel: "none", movementTag: "passive_rom" },
    { id: "acl-mini-squat", name: "미니 스쿼트 (부분 체중 부하)", description: "무릎 각도 30도 이내의 얕은 스쿼트, 체중의 일부만 부하", romMin: 0, romMax: 30, loadLevel: "light", movementTag: "closed_chain_partial" },
    { id: "acl-deep-squat", name: "풀 스쿼트", description: "무릎을 깊게 굽히는 전체 가동범위 스쿼트, 전체중 부하", romMin: 0, romMax: 140, loadLevel: "full", movementTag: "deep_squat" },
    { id: "acl-lateral-cut", name: "방향 전환 러닝 드릴", description: "급격한 회전·피벗이 포함된 민첩성 훈련", romMin: 0, romMax: 120, loadLevel: "full", movementTag: "pivoting" },
    { id: "acl-open-chain-ext", name: "레그 익스텐션 (저항 개방형 사슬)", description: "머신을 이용해 저항을 가하며 무릎을 펴는 개방형 사슬 운동", romMin: 0, romMax: 130, loadLevel: "moderate", movementTag: "open_chain_resisted" },
    { id: "acl-balance", name: "한발 서기 균형 훈련", description: "불안정 지지면 위에서 고유수용성감각 강화", romMin: 0, romMax: 30, loadLevel: "light", movementTag: "balance_proprioception" },
    { id: "acl-step-up", name: "스텝업", description: "낮은 스텝 박스를 이용한 단계적 체중 부하 훈련", romMin: 0, romMax: 100, loadLevel: "moderate", movementTag: "closed_chain_partial" },
  ],
  ROTATOR_CUFF: [
    { id: "rc-pendulum", name: "펜듈럼(진자) 운동", description: "상체를 숙이고 팔을 자연스럽게 흔들어 수동적으로 가동범위 확보", romMin: 0, romMax: 45, loadLevel: "none", movementTag: "passive_rom" },
    { id: "rc-passive-flex", name: "수동 전방 거상", description: "치료사 또는 반대손 보조로 팔을 천천히 들어올림", romMin: 0, romMax: 90, loadLevel: "none", movementTag: "passive_rom" },
    { id: "rc-aarom-pulley", name: "도르래를 이용한 능동보조 운동", description: "도르래 장비로 반대쪽 팔의 도움을 받아 거상", romMin: 0, romMax: 130, loadLevel: "light", movementTag: "active_assisted_rom" },
    { id: "rc-overhead-press", name: "오버헤드 프레스", description: "머리 위로 저항을 들어올리는 강한 부하의 운동", romMin: 0, romMax: 170, loadLevel: "full", movementTag: "overhead_press" },
    { id: "rc-er-endrange", name: "종말범위 외회전 스트레칭", description: "어깨 외회전을 최대 각도까지 강하게 스트레칭", romMin: 0, romMax: 90, loadLevel: "light", movementTag: "external_rotation_end_range" },
    { id: "rc-band-row", name: "밴드 로우", description: "탄력밴드를 이용한 저항성 개방형 사슬 운동", romMin: 0, romMax: 100, loadLevel: "moderate", movementTag: "open_chain_resisted" },
    { id: "rc-cuff-strength", name: "회전근개 저항 강화 운동", description: "덤벨/밴드를 이용한 내·외회전 근력 강화", romMin: 0, romMax: 90, loadLevel: "moderate", movementTag: "resisted_strengthening" },
  ],
  TKA: [
    { id: "tka-quad-iso", name: "대퇴사두근 등척성 운동", description: "무릎을 편 상태로 대퇴사두근 수축 유지", romMin: 0, romMax: 10, loadLevel: "none", movementTag: "quad_isometric" },
    { id: "tka-ankle-pump", name: "발목 펌프 운동", description: "혈전 예방을 위한 발목 굴곡/신전 반복", romMin: 0, romMax: 20, loadLevel: "none", movementTag: "passive_rom" },
    { id: "tka-gait", name: "보행기 보조 보행 훈련", description: "보조기구를 이용한 단계적 부분 체중 부하 보행", romMin: 0, romMax: 60, loadLevel: "light", movementTag: "gait_training" },
    { id: "tka-mini-squat", name: "미니 스쿼트", description: "낮은 각도의 부분 체중 부하 스쿼트", romMin: 0, romMax: 40, loadLevel: "moderate", movementTag: "closed_chain_partial" },
    { id: "tka-deep-squat", name: "풀 스쿼트", description: "무릎을 깊게 굽히는 전체 가동범위 스쿼트", romMin: 0, romMax: 140, loadLevel: "full", movementTag: "deep_squat" },
    { id: "tka-kneel", name: "무릎 꿇기 훈련", description: "바닥에 무릎을 대고 체중을 싣는 동작", romMin: 0, romMax: 130, loadLevel: "moderate", movementTag: "kneeling" },
    { id: "tka-pivot-drill", name: "방향 전환 보행 드릴", description: "걷는 중 급격히 방향을 전환하는 훈련", romMin: 0, romMax: 110, loadLevel: "full", movementTag: "pivoting" },
    { id: "tka-balance", name: "정적 균형 훈련", description: "평행봉을 잡고 서서 균형감각 회복", romMin: 0, romMax: 30, loadLevel: "light", movementTag: "balance_proprioception" },
  ],
};
