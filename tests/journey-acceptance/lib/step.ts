// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §4 Run Lifecycle step 7
// Constitutional basis: C-059 (Implementation Traceability), C-049 (Honest Limitation)
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { evaluateClaim } from "./claim.ts";
import { claimDefinition, stepIdentifiers } from "./plan.ts";
import type { PlanStep } from "./plan.ts";
import type { ClaimResult, DepthLevel, Finding, StepOutcome, Verdict, WitnessId, WitnessReading } from "./types.ts";

/** A prerequisite flag or precondition is off, so the step is reported as blocked, never as a pass or failure. */
export class BlockedByFlag extends Error {}

/** The step cannot be exercised at all in this environment and says so. */
export class NotCovered extends Error {}

export interface StepResult {
  readings: Record<string, WitnessReading[]>;
  reached: DepthLevel;
}

export interface ExecuteOptions {
  retries?: number;
}

function stepVerdict(claims: ClaimResult[]): Verdict {
  if (claims.some((claim) => claim.verdict === "FAIL")) {
    return "FAIL";
  }
  if (claims.some((claim) => claim.verdict === "NOT-WITNESSED")) {
    return "NOT-WITNESSED";
  }
  return "PASS";
}

function outcomeBase(step: PlanStep): Pick<StepOutcome, "stepId" | "title" | "identifiers" | "failurePath"> {
  return {
    stepId: step.id,
    title: step.title,
    identifiers: stepIdentifiers(step),
    failurePath: step.failure_path === true,
  };
}

/** Runs one plan step. Retries are explicit, bounded and recorded; a pass after a retry is FLAKY, never PASS. */
export async function executeStep(
  step: PlanStep,
  body: () => Promise<StepResult>,
  options: ExecuteOptions = {},
): Promise<StepOutcome> {
  const attempts = (options.retries ?? 0) + 1;
  let last: StepOutcome | undefined;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const result = await body();
      const claims = step.claims.map((claim) =>
        evaluateClaim(claimDefinition(claim), result.readings[claim.id] ?? []),
      );
      const verdict = stepVerdict(claims);
      const witnessesRead = [...new Set(claims.flatMap((claim) => claim.witnessesRead))] as WitnessId[];
      last = {
        ...outcomeBase(step),
        verdict,
        reached: result.reached,
        witnessesRead,
        claims,
        retries: attempt,
        reason: claims.filter((claim) => claim.verdict !== "PASS").map((claim) => claim.reason).join("; "),
      };
      if (verdict === "PASS") {
        return attempt > 0 ? { ...last, verdict: "FLAKY", reason: `passed on attempt ${attempt + 1}` } : last;
      }
      if (verdict === "NOT-WITNESSED") {
        return last;
      }
    } catch (error) {
      if (error instanceof BlockedByFlag) {
        return { ...outcomeBase(step), verdict: "BLOCKED-BY-FLAG", reached: null, witnessesRead: [], claims: [], retries: attempt, reason: error.message };
      }
      if (error instanceof NotCovered) {
        return { ...outcomeBase(step), verdict: "NOT-COVERED", reached: null, witnessesRead: [], claims: [], retries: attempt, reason: error.message };
      }
      last = {
        ...outcomeBase(step),
        verdict: "FAIL",
        reached: "L1",
        witnessesRead: [],
        claims: [],
        retries: attempt,
        reason: `step raised: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  }
  return last as StepOutcome;
}

const RESULTS = "results.jsonl";
const FINDINGS = "findings.jsonl";

export function recordOutcome(directory: string, outcome: StepOutcome): void {
  mkdirSync(directory, { recursive: true });
  appendFileSync(join(directory, RESULTS), `${JSON.stringify(outcome)}\n`);
}

export function recordFindings(directory: string, findings: Finding[]): void {
  mkdirSync(directory, { recursive: true });
  for (const finding of findings) {
    appendFileSync(join(directory, FINDINGS), `${JSON.stringify(finding)}\n`);
  }
}

function readLines<T>(path: string): T[] {
  if (!existsSync(path)) {
    return [];
  }
  return readFileSync(path, "utf8")
    .split("\n")
    .filter((line) => line.trim() !== "")
    .map((line) => JSON.parse(line) as T);
}

export function readOutcomes(directory: string): StepOutcome[] {
  return readLines<StepOutcome>(join(directory, RESULTS));
}

export function readFindings(directory: string): Finding[] {
  return readLines<Finding>(join(directory, FINDINGS));
}
