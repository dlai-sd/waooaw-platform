// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §8 Coverage And Depth Model (Report content)
// Constitutional basis: C-059 (Implementation Traceability), C-049 (Honest Limitation)
import { depthByIdentifier } from "./depth.ts";
import type { IdentifierDepth } from "./depth.ts";
import type { Plan } from "./plan.ts";
import { stepIdentifiers } from "./plan.ts";
import type { ProbeOutcome } from "./probe.ts";
import { VERDICTS } from "./types.ts";
import type { Finding, StepOutcome, Verdict } from "./types.ts";

export const REPORT_SCHEMA = "waooaw.acceptance-report/v1";

export interface ReportInput {
  environment: string;
  plan: Plan;
  planDigest: string;
  profileDigest: string;
  commit: string;
  services: { name: string; image: string }[];
  startedAt: string;
  finishedAt: string;
  outcomes: StepOutcome[];
  findings: Finding[];
  probe?: ProbeOutcome;
  providerModeFindings: string[];
  syntheticVolume: { customers_created: number; customers_removed: number; left_over: string[] };
  denominator: string[];
  declaredLimits: string[];
}

export interface Report {
  schema: string;
  verdict: Verdict;
  workflow_conclusion: "success" | "failure";
  candidate: {
    environment: string;
    journey_id: string;
    commit: string;
    journey_digest: string;
    profile_digest: string;
    services: { name: string; image: string }[];
    started_at: string;
    finished_at: string;
  };
  not_tested: {
    environment_unavailable: boolean;
    not_covered: { id: string; reason: string }[];
    not_covered_steps: { step: string; reason: string }[];
    not_witnessed: { step: string; reason: string }[];
    blocked_by_flag: { step: string; reason: string }[];
    flaky: { step: string; retries: number; reason: string }[];
    declared_limits: string[];
  };
  failures: { step: string; reason: string }[];
  guard_findings: Finding[];
  provider_mode_findings: string[];
  synthetic_volume: { customers_created: number; customers_removed: number; left_over: string[] };
  coverage: Record<string, IdentifierDepth>;
  steps: StepOutcome[];
  passed: string[];
}

const PRECEDENCE: Verdict[] = ["FAIL", "ENV-UNAVAILABLE", "NOT-WITNESSED", "FLAKY", "BLOCKED-BY-FLAG", "NOT-COVERED"];

/** Every plan step appears in the report: a step that did not run is NOT-COVERED (or ENV-UNAVAILABLE), never absent. */
export function completeOutcomes(plan: Plan, outcomes: StepOutcome[], environmentUnavailable: boolean): StepOutcome[] {
  return plan.steps.map((step) => {
    const found = outcomes.find((outcome) => outcome.stepId === step.id);
    if (found !== undefined) {
      return found;
    }
    return {
      stepId: step.id,
      title: step.title,
      verdict: environmentUnavailable ? "ENV-UNAVAILABLE" : "NOT-COVERED",
      identifiers: stepIdentifiers(step),
      reached: null,
      failurePath: step.failure_path === true,
      witnessesRead: [],
      claims: [],
      retries: 0,
      reason: environmentUnavailable ? "environment did not answer the readiness probe" : "step did not run",
    };
  });
}

export function overallVerdict(steps: StepOutcome[], findings: Finding[], environmentUnavailable: boolean): Verdict {
  if (environmentUnavailable) {
    return "ENV-UNAVAILABLE";
  }
  if (findings.length > 0 || steps.some((step) => step.verdict === "FAIL")) {
    return "FAIL";
  }
  for (const verdict of PRECEDENCE) {
    if (steps.some((step) => step.verdict === verdict)) {
      return verdict;
    }
  }
  return "PASS";
}

export function buildReport(input: ReportInput): Report {
  const environmentUnavailable = input.probe !== undefined && !input.probe.available;
  const steps = completeOutcomes(input.plan, input.outcomes, environmentUnavailable);
  const verdict = overallVerdict(steps, input.findings, environmentUnavailable);
  const coverage = depthByIdentifier(steps, input.denominator);
  return {
    schema: REPORT_SCHEMA,
    verdict,
    workflow_conclusion: verdict === "FAIL" || verdict === "ENV-UNAVAILABLE" ? "failure" : "success",
    candidate: {
      environment: input.environment,
      journey_id: input.plan.journey_id,
      commit: input.commit,
      journey_digest: input.planDigest,
      profile_digest: input.profileDigest,
      services: input.services,
      started_at: input.startedAt,
      finished_at: input.finishedAt,
    },
    not_tested: {
      environment_unavailable: environmentUnavailable,
      not_covered_steps: steps
        .filter((step) => step.verdict === "NOT-COVERED")
        .map((step) => ({ step: step.stepId, reason: step.reason })),
      not_covered: Object.entries(coverage)
        .filter(([, entry]) => entry.depth === "NOT-COVERED")
        .map(([id]) => ({ id, reason: "no step reached any depth for this identifier in this run" })),
      not_witnessed: steps
        .filter((step) => step.verdict === "NOT-WITNESSED")
        .map((step) => ({ step: step.stepId, reason: step.reason })),
      blocked_by_flag: steps
        .filter((step) => step.verdict === "BLOCKED-BY-FLAG")
        .map((step) => ({ step: step.stepId, reason: step.reason })),
      flaky: steps
        .filter((step) => step.verdict === "FLAKY")
        .map((step) => ({ step: step.stepId, retries: step.retries, reason: step.reason })),
      declared_limits: input.declaredLimits,
    },
    failures: steps.filter((step) => step.verdict === "FAIL").map((step) => ({ step: step.stepId, reason: step.reason })),
    guard_findings: input.findings,
    provider_mode_findings: input.providerModeFindings,
    synthetic_volume: input.syntheticVolume,
    coverage,
    steps,
    passed: steps.filter((step) => step.verdict === "PASS").map((step) => step.stepId),
  };
}

const COMMIT = /^[0-9a-f]{40}$/;
const DIGEST = /^[0-9a-f]{64}$/;

/** Structural validation mirrors validation/acceptance/report.schema.json; both are exercised against the same sample. */
export function validateReport(report: unknown): string[] {
  const errors: string[] = [];
  if (report === null || typeof report !== "object") {
    return ["report must be an object"];
  }
  const value = report as Record<string, unknown>;
  const keys = Object.keys(value);
  for (const required of [
    "schema",
    "verdict",
    "workflow_conclusion",
    "candidate",
    "not_tested",
    "failures",
    "guard_findings",
    "provider_mode_findings",
    "synthetic_volume",
    "coverage",
    "steps",
    "passed",
  ]) {
    if (!(required in value)) {
      errors.push(`missing ${required}`);
    }
  }
  if (value.schema !== REPORT_SCHEMA) {
    errors.push("schema identifier is wrong");
  }
  if (!VERDICTS.includes(value.verdict as Verdict)) {
    errors.push("verdict is outside the closed vocabulary");
  }
  if (keys.indexOf("not_tested") === -1 || keys.indexOf("not_tested") > keys.indexOf("passed")) {
    errors.push("not_tested must precede passed (C-049)");
  }
  const candidate = (value.candidate ?? {}) as Record<string, unknown>;
  if (!COMMIT.test(String(candidate.commit ?? ""))) {
    errors.push("candidate.commit must be a 40-character commit");
  }
  for (const field of ["journey_digest", "profile_digest"]) {
    if (!DIGEST.test(String(candidate[field] ?? ""))) {
      errors.push(`candidate.${field} must be a sha256 digest`);
    }
  }
  const tested = (value.not_tested ?? {}) as Record<string, unknown>;
  for (const field of ["not_covered", "not_covered_steps", "not_witnessed", "blocked_by_flag", "flaky", "declared_limits"]) {
    if (!Array.isArray(tested[field])) {
      errors.push(`not_tested.${field} must be a list`);
    }
  }
  const coverage = (value.coverage ?? {}) as Record<string, { depth?: string }>;
  for (const [identifier, entry] of Object.entries(coverage)) {
    if (!["L1", "L2", "L3", "L4", "L5", "NOT-COVERED"].includes(String(entry.depth))) {
      errors.push(`coverage.${identifier}.depth is invalid`);
    }
  }
  const steps = Array.isArray(value.steps) ? (value.steps as { verdict?: string }[]) : [];
  if (steps.some((step) => !VERDICTS.includes(step.verdict as Verdict))) {
    errors.push("a step verdict is outside the closed vocabulary");
  }
  return errors;
}

/** The summary lists what was not tested before what passed (C-049). */
export function renderSummary(report: Report): string {
  const lines: string[] = [];
  lines.push(`# Customer journey acceptance: ${report.verdict}`);
  lines.push("");
  lines.push(
    `Environment **${report.candidate.environment}**, journey **${report.candidate.journey_id}**, commit \`${report.candidate.commit.slice(0, 12)}\`.`,
  );
  lines.push("");
  lines.push("## Not tested");
  const tested = report.not_tested;
  if (tested.environment_unavailable) {
    lines.push("- The environment did not answer the readiness probe, so nothing was verified.");
  }
  for (const item of tested.blocked_by_flag) {
    lines.push(`- ${item.step} blocked by flag: ${item.reason}`);
  }
  for (const item of tested.not_witnessed) {
    lines.push(`- ${item.step} not witnessed: ${item.reason}`);
  }
  for (const item of tested.flaky) {
    lines.push(`- ${item.step} flaky after ${item.retries} retry(ies): ${item.reason}`);
  }
  for (const item of tested.not_covered_steps) {
    lines.push(`- ${item.step} not covered: ${item.reason}`);
  }
  for (const item of tested.not_covered) {
    lines.push(`- ${item.id} not covered by this run`);
  }
  for (const limit of tested.declared_limits) {
    lines.push(`- Limit: ${limit}`);
  }
  for (const finding of report.provider_mode_findings) {
    lines.push(`- Configuration finding: ${finding}`);
  }
  lines.push("");
  if (report.failures.length > 0 || report.guard_findings.length > 0) {
    lines.push("## Failed");
    for (const failure of report.failures) {
      lines.push(`- ${failure.step}: ${failure.reason}`);
    }
    for (const finding of report.guard_findings) {
      lines.push(`- Guard ${finding.guard} at ${finding.where}: ${finding.detail}`);
    }
    lines.push("");
  }
  lines.push("## Passed");
  lines.push(report.passed.length > 0 ? report.passed.map((id) => `- ${id}`).join("\n") : "- none");
  lines.push("");
  return lines.join("\n");
}
