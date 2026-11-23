// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §3 Components (Test plan loading)
// Constitutional basis: C-059 (Implementation Traceability)
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { ClaimDefinitionError } from "../lib/claim.ts";
import { claimDefinition, loadCompiledPlan, planStep, stepIdentifiers } from "../lib/plan.ts";
import { samplePlan } from "./support.ts";

function write(content: unknown): string {
  const path = join(mkdtempSync(join(tmpdir(), "ja-plan-")), "plan.json");
  writeFileSync(path, JSON.stringify(content));
  return path;
}

test("a compiled plan loads and exposes its steps and identifiers", () => {
  const loaded = loadCompiledPlan(write({ plan: samplePlan, planDigest: "a".repeat(64), liveScope: ["PG-11"] }));
  assert.equal(loaded.plan.journey_id, "sample");
  assert.deepEqual(stepIdentifiers(planStep(loaded.plan, "S1")), ["PG-02", "WC107-R009"]);
  assert.deepEqual(stepIdentifiers({ ...samplePlan.steps[0], proves: undefined }), []);
  assert.deepEqual(claimDefinition(samplePlan.steps[1].claims[0]).witnessesRequired, ["W1", "W2", "W3"]);
  assert.throws(() => planStep(loaded.plan, "S99"), /no step S99/);
});

test("a plan whose claim breaks the witness rule is refused at load time", () => {
  const broken = {
    ...samplePlan,
    steps: [{ ...samplePlan.steps[0], claims: [{ id: "S1-C1", statement: "s", witnesses_required: ["W1"] }] }],
  };
  assert.throws(() => loadCompiledPlan(write({ plan: broken, planDigest: "a".repeat(64), liveScope: [] })), ClaimDefinitionError);
});
