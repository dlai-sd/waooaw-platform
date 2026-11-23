// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §9 F4, F6
// Constitutional basis: C-059 (Implementation Traceability)
import assert from "node:assert/strict";
import { test } from "node:test";
import { ClaimDefinitionError, defineClaim, evaluateClaim, reading, unreadable } from "../lib/claim.ts";

const paid = defineClaim({ id: "S5-C1", statement: "Paid once", witnessesRequired: ["W1", "W2", "W3"] });

test("a claim with fewer than two witnesses is refused unless an exception carries a reason", () => {
  assert.throws(() => defineClaim({ id: "X", statement: "s", witnessesRequired: ["W1"] }), ClaimDefinitionError);
  assert.throws(() => defineClaim({ id: "X", statement: "s", witnessesRequired: ["W1", "W1"] }), ClaimDefinitionError);
  assert.throws(
    () => defineClaim({ id: "X", statement: "s", witnessesRequired: ["W1"], exception: { reason: "  " } }),
    ClaimDefinitionError,
  );
  const allowed = defineClaim({
    id: "X",
    statement: "s",
    witnessesRequired: ["W1"],
    exception: { reason: "no customer-reachable platform route exists" },
  });
  assert.deepEqual(allowed.witnessesRequired, ["W1"]);
  assert.throws(
    () => defineClaim({ id: "X", statement: "s", witnessesRequired: ["W9" as never, "W1"] }),
    ClaimDefinitionError,
  );
});

test("all required witnesses agreeing passes, regardless of key order in compared objects", () => {
  const result = evaluateClaim(paid, [
    reading("W1", { amount: 2360, state: "Active" }, { state: "Active", amount: 2360 }),
    reading("W2", ["a", { b: 1 }], ["a", { b: 1 }]),
    reading("W3", 2360, 2360),
  ]);
  assert.equal(result.verdict, "PASS");
  assert.deepEqual(result.witnessesRead, ["W1", "W2", "W3"]);
});

test("an unreadable required witness is NOT-WITNESSED and never a pass", () => {
  const result = evaluateClaim(paid, [
    reading("W1", "Active", "Active"),
    reading("W2", "Active", "Active"),
    unreadable("W3", "sandbox credential absent"),
  ]);
  assert.equal(result.verdict, "NOT-WITNESSED");
  assert.match(result.reason, /W3/);
  assert.equal(evaluateClaim(paid, []).verdict, "NOT-WITNESSED");
});

test("negative control: a stub that reports success without the provider agreeing yields FAIL", () => {
  // The screen and the platform both say paid; the provider sandbox, read independently, has no captured payment.
  const result = evaluateClaim(paid, [
    reading("W1", "Active", "Active"),
    reading("W2", "Active", "Active"),
    reading("W3", "captured", "not-found", "no payment for order"),
  ]);
  assert.equal(result.verdict, "FAIL");
  assert.match(result.reason, /W3/);
});

test("negative control: a stale cache shown on screen while the platform record differs yields FAIL", () => {
  const result = evaluateClaim(paid, [
    reading("W1", "Trial", "Active", "screen still shows the old state"),
    reading("W2", "Trial", "Trial"),
    reading("W3", "captured", "captured"),
  ]);
  assert.equal(result.verdict, "FAIL");
});

test("a disagreement outranks a missing witness, and a witness not required cannot change the verdict", () => {
  const result = evaluateClaim(paid, [reading("W1", 1, 2), unreadable("W2", "route absent")]);
  assert.equal(result.verdict, "FAIL");
  const two = defineClaim({ id: "T", statement: "s", witnessesRequired: ["W1", "W2"] });
  const ignored = evaluateClaim(two, [
    reading("W1", 1, 1),
    reading("W2", 1, 1),
    reading("W4", "x", "y", "telemetry disagrees but is not required"),
  ]);
  assert.equal(ignored.verdict, "PASS");
});
