// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §8 Report content, §9 F10, F17
// Constitutional basis: C-059 (Implementation Traceability), C-049 (Honest Limitation)
import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { passed, sampleInput, samplePlan } from "./support.ts";
import type { ProbeOutcome } from "../lib/probe.ts";
import { buildReport, completeOutcomes, overallVerdict, renderSummary, validateReport } from "../lib/report.ts";
import type { StepOutcome } from "../lib/types.ts";

const here = dirname(fileURLToPath(import.meta.url));

test("every plan step is reported and a step that did not run is NOT-COVERED", () => {
  const steps = completeOutcomes(samplePlan, [passed("S1", [])], false);
  assert.deepEqual(steps.map((step) => step.verdict), ["PASS", "NOT-COVERED"]);
  assert.deepEqual(completeOutcomes(samplePlan, [], true).map((step) => step.verdict), ["ENV-UNAVAILABLE", "ENV-UNAVAILABLE"]);
});

test("the report matches the committed sample and validates, with not-tested ahead of passed", () => {
  const report = buildReport(sampleInput());
  const samplePath = join(here, "..", "fixtures", "sample-report.json");
  if (process.env.WAOOAW_REGENERATE_SAMPLE_REPORT === "1") {
    writeFileSync(samplePath, `${JSON.stringify(report, null, 2)}\n`);
  }
  assert.deepEqual(validateReport(report), []);
  assert.deepEqual(report, JSON.parse(readFileSync(samplePath, "utf8")));
  const keys = Object.keys(report);
  assert.ok(keys.indexOf("not_tested") < keys.indexOf("passed"));
  assert.deepEqual(report.not_tested.not_covered.map((entry) => entry.id), ["PG-11"]);
  assert.deepEqual(report.not_tested.not_covered_steps.map((entry) => entry.step), ["S2"]);
});

test("the workflow conclusion is red only for FAIL or ENV-UNAVAILABLE", () => {
  const warn = (verdict: StepOutcome["verdict"]): StepOutcome => ({ ...passed("S2", ["PG-11"]), verdict, reached: null });
  for (const verdict of ["NOT-WITNESSED", "FLAKY", "BLOCKED-BY-FLAG", "NOT-COVERED"] as const) {
    const report = buildReport(sampleInput({ outcomes: [passed("S1", []), warn(verdict)] }));
    assert.equal(report.verdict, verdict);
    assert.equal(report.workflow_conclusion, "success");
  }
  const failed = buildReport(sampleInput({ outcomes: [passed("S1", []), warn("FAIL")] }));
  assert.equal(failed.workflow_conclusion, "failure");
  assert.deepEqual(failed.failures.map((entry) => entry.step), ["S2"]);
  const clean = buildReport(sampleInput({ outcomes: [passed("S1", []), passed("S2", [])] }));
  assert.equal(clean.verdict, "PASS");
  assert.equal(clean.workflow_conclusion, "success");
});

test("a guard finding fails an otherwise passing run, and an unavailable environment verifies nothing", () => {
  const steps = [passed("S1", []), passed("S2", [])];
  assert.equal(overallVerdict(steps, [{ guard: "g", where: "w", detail: "d" }], false), "FAIL");
  const down: ProbeOutcome = { available: false, results: [{ name: "web", ready: false, detail: "no answer" }] };
  const report = buildReport(sampleInput({ probe: down, outcomes: [] }));
  assert.equal(report.verdict, "ENV-UNAVAILABLE");
  assert.equal(report.workflow_conclusion, "failure");
  assert.equal(report.failures.length, 0);
  assert.equal(report.not_tested.environment_unavailable, true);
});

test("a malformed report is rejected on every structural rule", () => {
  assert.deepEqual(validateReport(null), ["report must be an object"]);
  const bad = { ...buildReport(sampleInput()), schema: "x", verdict: "MAYBE", steps: [{ verdict: "?" }] } as Record<string, unknown>;
  bad.candidate = { commit: "short", journey_digest: "x", profile_digest: "y" };
  bad.not_tested = { not_covered: "no" };
  bad.coverage = { "PG-01": { depth: "L9" } };
  const errors = validateReport(bad);
  for (const expected of [
    "schema identifier is wrong",
    "verdict is outside the closed vocabulary",
    "candidate.commit must be a 40-character commit",
    "candidate.journey_digest must be a sha256 digest",
    "not_tested.not_covered must be a list",
    "coverage.PG-01.depth is invalid",
    "a step verdict is outside the closed vocabulary",
  ]) {
    assert.ok(errors.includes(expected), expected);
  }
  const base = buildReport(sampleInput()) as unknown as Record<string, unknown>;
  const { passed: passedList, ...rest } = base;
  assert.ok(validateReport(rest).includes("missing passed"));
  assert.ok(validateReport({ passed: passedList, ...rest }).includes("not_tested must precede passed (C-049)"));
});

test("the summary lists what was not tested before what passed", () => {
  const summary = renderSummary(
    buildReport(
      sampleInput({
        outcomes: [passed("S1", ["PG-02"]), { ...passed("S2", []), verdict: "BLOCKED-BY-FLAG", reason: "no offerable price", reached: null }],
        findings: [{ guard: "wcag_2_1_aa", where: "/", detail: "color-contrast" }],
      }),
    ),
  );
  assert.ok(summary.indexOf("## Not tested") < summary.indexOf("## Passed"));
  assert.match(summary, /S2 blocked by flag: no offerable price/);
  assert.match(summary, /## Failed/);
  assert.match(summary, /Guard wcag_2_1_aa/);
  const withFinding = renderSummary(buildReport(sampleInput({ providerModeFindings: ["Key Vault secrets not readable from this runner: x"] })));
  assert.match(withFinding, /Configuration finding: Key Vault secrets not readable/);
  const unavailable = renderSummary(buildReport(sampleInput({ probe: { available: false, results: [] }, outcomes: [] })));
  assert.match(unavailable, /nothing was verified/);
  const flaky = renderSummary(buildReport(sampleInput({ outcomes: [{ ...passed("S1", []), verdict: "FLAKY", retries: 1, reason: "passed on attempt 2" }, { ...passed("S2", []), verdict: "NOT-WITNESSED", reason: "W3 absent", reached: "L1" }] })));
  assert.match(flaky, /flaky after 1 retry/);
  assert.match(flaky, /not witnessed: W3 absent/);
  assert.match(renderSummary(buildReport(sampleInput({ outcomes: [] }))), /- none/);
});
