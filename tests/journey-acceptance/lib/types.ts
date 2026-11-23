// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 Oracle Read Contract
// Constitutional basis: C-059 (Implementation Traceability)

export const VERDICTS = [
  "PASS",
  "FAIL",
  "BLOCKED-BY-FLAG",
  "NOT-COVERED",
  "NOT-WITNESSED",
  "ENV-UNAVAILABLE",
  "FLAKY",
] as const;
export type Verdict = (typeof VERDICTS)[number];

export const WITNESSES = ["W1", "W2", "W3", "W4"] as const;
export type WitnessId = (typeof WITNESSES)[number];

export const DEPTH_LEVELS = ["L1", "L2", "L3", "L4", "L5"] as const;
export type DepthLevel = (typeof DEPTH_LEVELS)[number];

export function depthRank(level: DepthLevel): number {
  return DEPTH_LEVELS.indexOf(level) + 1;
}

export function rankToDepth(rank: number): DepthLevel | null {
  return rank >= 1 && rank <= DEPTH_LEVELS.length ? DEPTH_LEVELS[rank - 1] : null;
}

export interface WitnessReading {
  witness: WitnessId;
  readable: boolean;
  holds?: boolean;
  detail?: string;
}

export interface ClaimDefinition {
  id: string;
  statement: string;
  witnessesRequired: WitnessId[];
  exception?: { reason: string };
  depthTarget?: DepthLevel;
}

export interface ClaimResult {
  claimId: string;
  verdict: Verdict;
  witnessesRead: WitnessId[];
  reason: string;
}

export interface Finding {
  guard: string;
  where: string;
  detail: string;
}

export interface StepOutcome {
  stepId: string;
  title: string;
  verdict: Verdict;
  identifiers: string[];
  reached: DepthLevel | null;
  failurePath: boolean;
  witnessesRead: WitnessId[];
  claims: ClaimResult[];
  retries: number;
  reason: string;
}
