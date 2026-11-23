// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §9 F15
// Constitutional basis: C-059 (Implementation Traceability)
import assert from "node:assert/strict";
import { test } from "node:test";
import { probeEnvironment } from "../lib/probe.ts";

const targets = [
  { name: "web", url: "https://web.example/" },
  { name: "keycloak", url: "https://auth.example/realms/waooaw" },
];

test("an environment that answers on every target is available", async () => {
  const outcome = await probeEnvironment(targets, {
    timeoutMs: 100,
    fetchImpl: async () => ({ status: 200 }),
  });
  assert.equal(outcome.available, true);
  assert.deepEqual(outcome.results.map((result) => result.detail), ["HTTP 200", "HTTP 200"]);
});

test("a server error or an unreachable target makes the environment unavailable", async () => {
  const outcome = await probeEnvironment(targets, {
    timeoutMs: 100,
    fetchImpl: async (url) => {
      if (url.includes("auth")) {
        throw new Error("connect ECONNREFUSED");
      }
      return { status: 503 };
    },
  });
  assert.equal(outcome.available, false);
  assert.match(outcome.results[0].detail, /503/);
  assert.match(outcome.results[1].detail, /ECONNREFUSED/);
});

test("a stopped environment is reported within the probe timeout", async () => {
  const started = Date.now();
  const outcome = await probeEnvironment(targets, {
    timeoutMs: 50,
    fetchImpl: (_url, init) =>
      new Promise((_resolve, reject) => {
        init.signal.addEventListener("abort", () => reject(new Error("aborted")));
      }),
  });
  assert.equal(outcome.available, false);
  assert.match(outcome.results[0].detail, /no answer within 50 ms/);
  assert.ok(Date.now() - started < 1000);
});

test("the default transport is the platform fetch", async () => {
  const outcome = await probeEnvironment([{ name: "bad", url: "http://127.0.0.1:1/" }], { timeoutMs: 200 });
  assert.equal(outcome.available, false);
});
