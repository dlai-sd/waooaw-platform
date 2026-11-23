// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §8 Coverage And Depth Model
// Constitutional basis: C-059 (Implementation Traceability)
import type { DepthLevel, StepOutcome } from "./types.ts";
import { depthRank, rankToDepth } from "./types.ts";

export interface IdentifierDepth {
  depth: DepthLevel | "NOT-COVERED";
  steps: string[];
}

/**
 * Depth is what the witnesses proved, never what the spec hoped for: L3 and above need the platform record (W2),
 * L5 needs a declared failure path, and anything that did not PASS stops at L2 at most.
 */
export function effectiveDepth(outcome: StepOutcome): DepthLevel | null {
  if (outcome.reached === null) {
    return null;
  }
  if (["BLOCKED-BY-FLAG", "NOT-COVERED", "ENV-UNAVAILABLE"].includes(outcome.verdict)) {
    return null;
  }
  let rank = depthRank(outcome.reached);
  if (outcome.verdict !== "PASS" && outcome.verdict !== "FLAKY") {
    rank = Math.min(rank, 2);
  }
  if (!outcome.witnessesRead.includes("W2")) {
    rank = Math.min(rank, 2);
  }
  if (rank >= 5 && !outcome.failurePath) {
    rank = 4;
  }
  return rankToDepth(rank);
}

export function depthByIdentifier(
  outcomes: StepOutcome[],
  denominator: string[],
): Record<string, IdentifierDepth> {
  const result: Record<string, IdentifierDepth> = {};
  for (const identifier of [...new Set(denominator)].sort()) {
    let best = 0;
    const steps: string[] = [];
    for (const outcome of outcomes) {
      if (!outcome.identifiers.includes(identifier)) {
        continue;
      }
      const depth = effectiveDepth(outcome);
      if (depth === null) {
        continue;
      }
      steps.push(outcome.stepId);
      best = Math.max(best, depthRank(depth));
    }
    const depth = rankToDepth(best);
    result[identifier] = { depth: depth ?? "NOT-COVERED", steps };
  }
  return result;
}
