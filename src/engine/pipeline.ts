import { EXERCISE_LIBRARY } from "../data/exercises";
import { findRule } from "../data/rules";
import {
  LOAD_LABEL,
  LOAD_ORDER,
  type AttemptRecord,
  type CorrectionLogEntry,
  type ExerciseSpec,
  type LoadLevel,
  type PatientInput,
  type PipelineResult,
  type PrescriptionItem,
  type ValidationIssue,
} from "../types";

const REPLACEMENT_TAG_MAP: Record<string, string[]> = {
  deep_squat: ["closed_chain_partial", "quad_isometric"],
  pivoting: ["balance_proprioception", "closed_chain_partial", "gait_training"],
  open_chain_resisted: ["passive_rom", "active_assisted_rom", "closed_chain_partial"],
  overhead_press: ["active_assisted_rom", "passive_rom"],
  external_rotation_end_range: ["passive_rom", "active_assisted_rom"],
  kneeling: ["closed_chain_partial", "gait_training"],
};

function hashString(input: string): number {
  let hash = 5381;
  for (let i = 0; i < input.length; i++) {
    hash = (hash * 33) ^ input.charCodeAt(i);
  }
  return Math.abs(hash);
}

function describeItem(item: { name: string; romMin: number; romMax: number; loadLevel: LoadLevel }): string {
  return `${item.name} · 가동범위 ${item.romMin}~${item.romMax}° · ${LOAD_LABEL[item.loadLevel]}`;
}

function deriveSetsReps(tag: string): string {
  if (tag === "quad_isometric") return "3세트 x 10회, 5초 유지";
  if (tag === "passive_rom") return "2세트 x 10회";
  if (tag === "active_assisted_rom") return "3세트 x 10회";
  if (tag === "balance_proprioception") return "3세트 x 30초 유지";
  if (tag === "gait_training") return "1일 3회, 5~10분";
  if (tag === "closed_chain_partial") return "3세트 x 12회";
  if (tag === "resisted_strengthening") return "3세트 x 10회";
  return "3세트 x 10회";
}

function toPrescriptionItem(spec: ExerciseSpec): PrescriptionItem {
  return { ...spec, setsReps: deriveSetsReps(spec.movementTag) };
}

function generatePrescription(input: PatientInput, seed: number): PrescriptionItem[] {
  const library = EXERCISE_LIBRARY[input.surgeryType];
  const rule = findRule(input.surgeryType, input.recoveryWeek);
  const items: PrescriptionItem[] = [];
  const usedIds = new Set<string>();

  // 1) 단계별 필수 운동 태그 커버 (Generator가 항상 챙기는 부분)
  rule.requiredMovementTags.forEach((tag, i) => {
    const candidates = library.filter((e) => e.movementTag === tag);
    if (candidates.length === 0) return;
    const pick = candidates[(seed + i) % candidates.length];
    if (!usedIds.has(pick.id)) {
      items.push(toPrescriptionItem(pick));
      usedIds.add(pick.id);
    }
  });

  // 2) 전체 라이브러리에서 추가 운동을 결정적(seed 기반)으로 채워 넣음
  //    -> 실제로 AI 생성 시 자주 발생하는 "금기/상한 누락" 상황을 재현
  const extraCount = 3;
  for (let i = 0; i < extraCount; i++) {
    const idx = (seed * 7 + i * 13 + input.recoveryWeek) % library.length;
    const pick = library[idx];
    if (!usedIds.has(pick.id)) {
      items.push(toPrescriptionItem(pick));
      usedIds.add(pick.id);
    }
  }

  return items;
}

function validatePrescription(
  items: PrescriptionItem[],
  rule: ReturnType<typeof findRule>,
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  for (const item of items) {
    if (item.romMax > rule.romLimit[1]) {
      issues.push({
        itemId: item.id,
        itemName: item.name,
        ruleId: rule.id,
        type: "ROM_EXCEEDED",
        detail: `가동범위 상한 ${item.romMax}°가 ${rule.stageLabel} 허용 상한 ${rule.romLimit[1]}°를 초과`,
      });
    }
    if (LOAD_ORDER.indexOf(item.loadLevel) > LOAD_ORDER.indexOf(rule.loadLimit)) {
      issues.push({
        itemId: item.id,
        itemName: item.name,
        ruleId: rule.id,
        type: "LOAD_EXCEEDED",
        detail: `부하 단계 '${LOAD_LABEL[item.loadLevel]}'가 ${rule.stageLabel} 허용 상한 '${LOAD_LABEL[rule.loadLimit]}'를 초과`,
      });
    }
    if (rule.forbiddenMovementTags.includes(item.movementTag)) {
      issues.push({
        itemId: item.id,
        itemName: item.name,
        ruleId: rule.id,
        type: "FORBIDDEN_MOVEMENT",
        detail: `${rule.stageLabel}에서 금기로 지정된 동작 패턴(${item.movementTag}) 포함`,
      });
    }
  }

  for (const tag of rule.requiredMovementTags) {
    if (!items.some((it) => it.movementTag === tag)) {
      issues.push({
        itemId: `__missing_${tag}`,
        itemName: tag,
        ruleId: rule.id,
        type: "MISSING_REQUIRED_ITEM",
        detail: `${rule.stageLabel}에 필수인 운동 유형(${tag})이 처방에 누락됨`,
      });
    }
  }

  return issues;
}

function findAlternative(
  rule: ReturnType<typeof findRule>,
  library: ExerciseSpec[],
  excludeIds: Set<string>,
  preferredTags: string[],
): ExerciseSpec {
  const compliant = library.filter(
    (e) =>
      !excludeIds.has(e.id) &&
      e.romMax <= rule.romLimit[1] &&
      LOAD_ORDER.indexOf(e.loadLevel) <= LOAD_ORDER.indexOf(rule.loadLimit) &&
      !rule.forbiddenMovementTags.includes(e.movementTag),
  );
  const preferred = compliant.find((e) => preferredTags.includes(e.movementTag));
  return preferred ?? compliant[0] ?? library[0];
}

function correctPrescription(
  items: PrescriptionItem[],
  issues: ValidationIssue[],
  rule: ReturnType<typeof findRule>,
  input: PatientInput,
): { items: PrescriptionItem[]; log: CorrectionLogEntry[] } {
  const library = EXERCISE_LIBRARY[input.surgeryType];
  const usedIds = new Set(items.map((it) => it.id));
  const log: CorrectionLogEntry[] = [];
  let nextItems = [...items];

  const issuesByItem = new Map<string, ValidationIssue[]>();
  for (const issue of issues) {
    if (issue.type === "MISSING_REQUIRED_ITEM") continue;
    const list = issuesByItem.get(issue.itemId) ?? [];
    list.push(issue);
    issuesByItem.set(issue.itemId, list);
  }

  for (const [itemId, itemIssues] of issuesByItem) {
    const idx = nextItems.findIndex((it) => it.id === itemId);
    if (idx === -1) continue;
    const before = nextItems[idx];
    const hasForbidden = itemIssues.some((i) => i.type === "FORBIDDEN_MOVEMENT");

    if (hasForbidden) {
      usedIds.delete(before.id);
      const preferredTags = REPLACEMENT_TAG_MAP[before.movementTag] ?? [];
      const alt = findAlternative(rule, library, usedIds, preferredTags);
      const after = toPrescriptionItem(alt);
      usedIds.add(after.id);
      nextItems[idx] = after;
      log.push({
        itemId: before.id,
        itemName: before.name,
        ruleId: rule.id,
        before: describeItem(before),
        after: describeItem(after),
        reason: `금기 동작(${before.movementTag}) → 규칙 통과 대체 운동으로 교체`,
      });
    } else {
      const clampedRomMax = Math.min(before.romMax, rule.romLimit[1]);
      const clampedLoadIdx = Math.min(LOAD_ORDER.indexOf(before.loadLevel), LOAD_ORDER.indexOf(rule.loadLimit));
      const after: PrescriptionItem = {
        ...before,
        romMax: clampedRomMax,
        loadLevel: LOAD_ORDER[clampedLoadIdx],
      };
      nextItems[idx] = after;
      log.push({
        itemId: before.id,
        itemName: before.name,
        ruleId: rule.id,
        before: describeItem(before),
        after: describeItem(after),
        reason: itemIssues.map((i) => (i.type === "ROM_EXCEEDED" ? "가동범위 상한 초과" : "부하 단계 초과")).join(", ") + " → 단계별 상한에 맞게 파라미터 조정",
      });
    }
  }

  const missingIssues = issues.filter((i) => i.type === "MISSING_REQUIRED_ITEM");
  for (const issue of missingIssues) {
    const tag = issue.itemName;
    const alt = findAlternative(rule, library, usedIds, [tag]);
    const after = toPrescriptionItem(alt);
    usedIds.add(after.id);
    nextItems.push(after);
    log.push({
      itemId: after.id,
      itemName: after.name,
      ruleId: rule.id,
      before: "(누락)",
      after: describeItem(after),
      reason: `필수 운동 유형(${tag}) 누락 → 처방에 추가`,
    });
  }

  return { items: nextItems, log };
}

const MAX_CORRECTION_ROUNDS = 2;

function runOnce(input: PatientInput): AttemptRecord[] {
  const rule = findRule(input.surgeryType, input.recoveryWeek);
  const seed = hashString(`${input.surgeryType}-${input.recoveryWeek}-${input.age}-${input.graftType}`);

  const attempts: AttemptRecord[] = [];
  let currentItems = generatePrescription(input, seed);
  let currentIssues = validatePrescription(currentItems, rule);
  attempts.push({ attempt: 1, prescription: currentItems, issues: currentIssues, corrections: [] });

  let round = 0;
  while (currentIssues.length > 0 && round < MAX_CORRECTION_ROUNDS) {
    round += 1;
    const { items: correctedItems, log } = correctPrescription(currentItems, currentIssues, rule, input);
    currentItems = correctedItems;
    currentIssues = validatePrescription(currentItems, rule);
    attempts.push({ attempt: round + 1, prescription: currentItems, issues: currentIssues, corrections: log });
  }

  return attempts;
}

export function runPipeline(input: PatientInput): PipelineResult {
  const rule = findRule(input.surgeryType, input.recoveryWeek);
  const attempts = runOnce(input);
  const finalPrescription = attempts[attempts.length - 1].prescription;
  const finalIssueCount = attempts[attempts.length - 1].issues.length;

  // 동일 입력 재현성 검증: 같은 입력으로 pipeline을 반복 실행해도
  // 매번 최종 위반 0건에 도달하는지 확인 (성공 기준 3)
  const consistencyRuns = [0, 1, 2].map(() => {
    const result = runOnce(input);
    return result[result.length - 1].issues.length === 0;
  });

  return { input, rule, attempts, finalPrescription, finalIssueCount, consistencyRuns };
}
