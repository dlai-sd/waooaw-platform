// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §4 Run Lifecycle step 7
// Constitutional basis: C-059 (Implementation Traceability)
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { reading, unreadable } from "../lib/claim.ts";
import type { PlanStep } from "../lib/plan.ts";
import { BlockedByFlag, NotCovered, executeStep, readFindings, readOutcomes, recordFindings, recordOutcome } from "../lib/step.ts";

const step: PlanStep = {
  id: "S3",
  title: "Start trial",
  customer: "A",
  stimulus: "start the trial",
  claims: [{ id: "S3-C1", statement: "trial active", witnesses_required: ["W1", "W2"] }],
  proves: { requirements: ["WC107-R010"], gaps: ["PG-08"] },
};

const agree = { readings: { "S3-C1": [reading("W1", "Trial", "Trial"), reading("W2", "Trial", "Trial")] }, reached: "L4" as const };

test("a step whose witnesses agree passes and carries its identifiers", async () => {
  const outcome = await executeStep(step, async () => agree);
  assert.equal(outcome.verdict, "PASS");
  assert.deepEqual(outcome.identifiers, ["PG-08", "WC107-R010"]);
  assert.equal(outcome.retries, 0);
});

test("a disagreeing witness fails the step and a missing required witness is NOT-WITNESSED", async () => {
  const failed = await executeStep(step, async () => ({
    readings: { "S3-C1": [reading("W1", "Trial", "Active"), reading("W2", "Trial", "Trial")] },
    reached: "L2",
  }));
  assert.equal(failed.verdict, "FAIL");
  const unseen = await executeStep(step, async () => ({
    readings: { "S3-C1": [reading("W1", "Trial", "Trial"), unreadable("W2", "route absent")] },
    reached: "L2",
  }));
  assert.equal(unseen.verdict, "NOT-WITNESSED");
});

test("a pass only after a retry is FLAKY, and the retry is recorded", async () => {
  let calls = 0;
  const outcome = await executeStep(
    step,
    async () => {
      calls += 1;
      return calls === 1
        ? { readings: { "S3-C1": [reading("W1", 1, 2), reading("W2", 1, 1)] }, reached: "L2" as const }
        : agree;
    },
    { retries: 1 },
  );
  assert.equal(outcome.verdict, "FLAKY");
  assert.equal(outcome.retries, 1);
  assert.equal(calls, 2);
});

test("a step that keeps failing stops after its bounded attempts", async () => {
  let calls = 0;
  const outcome = await executeStep(
    step,
    async () => {
      calls += 1;
      throw new Error("selector not found");
    },
    { retries: 2 },
  );
  assert.equal(outcome.verdict, "FAIL");
  assert.equal(calls, 3);
  assert.match(outcome.reason, /selector not found/);
  const stringError = await executeStep(step, async () => Promise.reject("plain"));
  assert.match(stringError.reason, /plain/);
});

test("flag and coverage blocks are reported with their reason, never as pass or failure", async () => {
  const blocked = await executeStep(step, async () => {
    throw new BlockedByFlag("no offerable price");
  });
  assert.equal(blocked.verdict, "BLOCKED-BY-FLAG");
  assert.equal(blocked.reason, "no offerable price");
  const uncovered = await executeStep(step, async () => {
    throw new NotCovered("no customer path");
  });
  assert.equal(uncovered.verdict, "NOT-COVERED");
});

test("outcomes and guard findings round-trip through the run directory", async () => {
  const directory = join(mkdtempSync(join(tmpdir(), "ja-run-")), "out");
  assert.deepEqual(readOutcomes(directory), []);
  recordOutcome(directory, await executeStep(step, async () => agree));
  recordFindings(directory, [{ guard: "g", where: "w", detail: "d" }]);
  assert.equal(readOutcomes(directory).length, 1);
  assert.equal(readFindings(directory)[0].guard, "g");
});
