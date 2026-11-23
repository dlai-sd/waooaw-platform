// Implements: validation/acceptance/rollup.v1.yaml (WC107-R019); architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 W4
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)
import assert from "node:assert/strict";
import { test } from "node:test";
import { parseSetCookie } from "../lib/cookies.ts";
import { renderRollup, rollup } from "../lib/rollup.ts";
import type { RollupMap, RollupReport } from "../lib/rollup.ts";
import { buildKql, correlationId, summarizeTelemetry } from "../lib/telemetry.ts";
import { buildReport, validateReport } from "../lib/report.ts";
import { passed, sampleInput } from "./support.ts";

const map: RollupMap = {
  requirement: "WC107-R019",
  devices: ["desktop", "mobile"],
  journeys: [
    { id: "login", title: "Login", steps: ["S2"] },
    { id: "registration", title: "Registration", steps: [], reason: "not exercised by synthetic users" },
    { id: "trial", title: "Trial", steps: ["S3", "S11"] },
  ],
};

function report(device: string, verdicts: Record<string, string>, overrides: Partial<RollupReport["candidate"]> = {}): RollupReport {
  return {
    candidate: {
      commit: "c".repeat(40),
      device,
      environment: "demo",
      finished_at: "2026-11-23T10:00:00.000Z",
      services: [{ name: "web", image: "r/web@sha256:" + "a".repeat(64) }],
      ...overrides,
    },
    steps: Object.entries(verdicts).map(([stepId, verdict]) => ({ stepId, verdict })),
  };
}

test("a journey with no steps keeps the requirement open even when everything else passes", () => {
  const all = { S2: "PASS", S3: "PASS", S11: "PASS" };
  const result = rollup(map, [report("desktop", all), report("mobile", all)]);
  assert.equal(result.status, "OPEN");
  const registration = result.cells.filter((cell) => cell.journey === "registration");
  assert.deepEqual(registration.map((cell) => cell.status), ["NOT-COVERED", "NOT-COVERED"]);
  assert.equal(result.cells.filter((cell) => cell.status === "PASS").length, 4);
  assert.match(renderRollup(result), /registration on desktop: NOT-COVERED \(not exercised by synthetic users\)/);
});

test("the rollup passes only when every journey passes on every device for one candidate", () => {
  const complete: RollupMap = { ...map, journeys: map.journeys.filter((journey) => journey.steps.length > 0) };
  const all = { S2: "PASS", S3: "PASS", S11: "PASS" };
  const passing = rollup(complete, [report("desktop", all), report("mobile", all)]);
  assert.equal(passing.status, "PASS");
  assert.equal(passing.candidate?.commit, "c".repeat(40));
  assert.match(renderRollup(passing), /## Open\n- none/);
});

test("a missing device, a failing step and the worst verdict are reported", () => {
  const complete: RollupMap = { ...map, journeys: [map.journeys[2]] };
  const result = rollup(complete, [report("desktop", { S3: "NOT-WITNESSED", S11: "FAIL" })]);
  const desktop = result.cells.find((cell) => cell.device === "desktop");
  const mobile = result.cells.find((cell) => cell.device === "mobile");
  assert.equal(desktop?.status, "FAIL");
  assert.deepEqual(desktop?.reasons, ["S3 is NOT-WITNESSED on desktop", "S11 is FAIL on desktop"]);
  assert.equal(mobile?.status, "MISSING");
  assert.equal(result.status, "OPEN");
});

test("the newest report for a device decides a step", () => {
  const complete: RollupMap = { ...map, journeys: [map.journeys[0]], devices: ["desktop"] };
  const older = report("desktop", { S2: "FAIL" }, { finished_at: "2026-11-23T09:00:00.000Z" });
  const newer = report("desktop", { S2: "PASS" }, { finished_at: "2026-11-23T10:00:00.000Z" });
  assert.equal(rollup(complete, [older, newer]).status, "PASS");
});

test("reports for different commits or images never combine into one proof", () => {
  const complete: RollupMap = { ...map, journeys: [map.journeys[0]] };
  const other = report("mobile", { S2: "PASS" }, { commit: "d".repeat(40) });
  const images = report("mobile", { S2: "PASS" }, { services: [{ name: "web", image: "r/web@sha256:" + "b".repeat(64) }] });
  const mismatched = rollup(complete, [report("desktop", { S2: "PASS" }), other, images]);
  assert.equal(mismatched.status, "OPEN");
  assert.equal(mismatched.mismatches.length, 2);
  assert.match(mismatched.mismatches[0], /commit/);
  assert.match(mismatched.mismatches[1], /different service images/);
  const none = rollup(complete, []);
  assert.equal(none.status, "OPEN");
  assert.equal(none.candidate, null);
  assert.deepEqual(none.mismatches, ["no report was supplied"]);
  assert.match(renderRollup(none), /Candidate mismatch: no report was supplied/);
});

test("the telemetry query is built only from safe inputs and carries a poll nonce", () => {
  const id = correlationId("AbC_123-xyz");
  assert.equal(id, "acc-abc123xyz");
  const kql = buildKql(id, "2026-11-23T10:00:00.000Z", "n-1");
  assert.match(kql, /^\/\/ poll n-1\n/);
  assert.match(kql, /Log_s has "acc-abc123xyz"/);
  assert.throws(() => buildKql('acc-x" | drop', "2026-11-23T10:00:00.000Z", "n"), /safe forms/);
  assert.throws(() => buildKql(id, "now()", "n"), /safe forms/);
  assert.throws(() => buildKql(id, "2026-11-23T10:00:00.000Z", "n; x"), /safe forms/);
});

test("telemetry is reported honestly whether it was not read, empty or seen", () => {
  assert.equal(summarizeTelemetry(undefined, "acc-1").source, "none");
  assert.match(summarizeTelemetry(undefined, "acc-1").note, /WC107-R018 stays unproven/);
  const empty = summarizeTelemetry([], "acc-1");
  assert.equal(empty.source, "console-log");
  assert.match(empty.note, /no service logged/);
  const seen = summarizeTelemetry([{ service: "web", lines: 4 }, { service: "bp", lines: 9 }], "acc-1");
  assert.deepEqual(seen.services.map((service) => service.name), ["bp", "web"]);
  assert.match(seen.note, /2 service\(s\).*still not witnessed/);
});

test("the My Agents hand-off cookie is parsed with its attributes, and an absent cookie is undefined", () => {
  const raw = "other=1; Path=/\nwaooaw_my_agents_selection=abc123; Path=/professionals/mine; Expires=x; HttpOnly; Secure; SameSite=Strict";
  assert.deepEqual(parseSetCookie(raw, "waooaw_my_agents_selection"), {
    name: "waooaw_my_agents_selection",
    value: "abc123",
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    path: "/professionals/mine",
  });
  assert.equal(parseSetCookie(raw, "missing"), undefined);
  assert.equal(parseSetCookie("garbage", "garbage"), undefined);
  assert.equal(parseSetCookie("plain=1", "plain")?.httpOnly, false);
});

test("exploratory notes ride along but can never change the verdict or the conclusion", () => {
  const without = buildReport(sampleInput({ outcomes: [passed("S1", []), passed("S2", [])] }));
  const withNotes = buildReport(sampleInput({ outcomes: [passed("S1", []), passed("S2", [])], exploratoryNotes: ["the second page looked slow"] }));
  assert.equal(withNotes.verdict, without.verdict);
  assert.equal(withNotes.workflow_conclusion, without.workflow_conclusion);
  assert.deepEqual(withNotes.exploratory_notes, ["the second page looked slow"]);
  assert.deepEqual(without.exploratory_notes, []);
  assert.equal(withNotes.candidate.device, "desktop");
  const mobile = buildReport(sampleInput({ device: "mobile", runId: "run1" }));
  assert.equal(mobile.candidate.device, "mobile");
  assert.equal(mobile.telemetry.correlation_id, "acc-run1");
  const broken = { ...mobile, candidate: { ...mobile.candidate, device: "tablet" }, telemetry: { source: "x" }, exploratory_notes: "no" } as unknown;
  const errors = validateReport(broken);
  assert.ok(errors.includes("candidate.device must be desktop or mobile"));
  assert.ok(errors.includes("telemetry.source must be console-log or none"));
  assert.ok(errors.includes("exploratory_notes must be a list"));
});
