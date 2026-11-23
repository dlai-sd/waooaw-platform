// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §4 Run Lifecycle, §9 F8, F13, F15, F18
// Constitutional basis: C-059 (Implementation Traceability)
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { samplePlan } from "./support.ts";

const here = dirname(fileURLToPath(import.meta.url));
const runner = join(here, "..", "run.ts");

function workspace(probeUrl: string): { out: string; privateDir: string } {
  const root = mkdtempSync(join(tmpdir(), "ja-cli-"));
  const out = join(root, "out");
  const privateDir = join(root, "private");
  mkdirSync(out);
  mkdirSync(privateDir);
  writeFileSync(join(out, "plan.json"), JSON.stringify({ plan: samplePlan, planDigest: "a".repeat(64), liveScope: ["PG-11"] }));
  writeFileSync(
    join(out, "profile.json"),
    JSON.stringify({
      environment: "demo",
      probes: [{ name: "web", url: probeUrl }],
      probe_timeout_ms: 1500,
      profile_digest: "b".repeat(64),
      origins: { web: "http://127.0.0.1:1", api: "", identity: "" },
      keycloak: { realm: "waooaw", username_prefix: "acc-", email_domain: "synthetic.waooaw.test", synthetic_group: "synthetic" },
    }),
  );
  return { out, privateDir };
}

function run(args: string[], env: NodeJS.ProcessEnv = {}): Promise<{ status: number | null; stderr: string }> {
  return new Promise((resolve) => {
    const child = spawn("node", [runner, ...args], { env: { ...process.env, ...env } });
    let stderr = "";
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    child.on("close", (status) => resolve({ status, stderr }));
  });
}

const commit = "c".repeat(40);

test("a stopped environment yields ENV-UNAVAILABLE with a red conclusion and zero step failures", async () => {
  const { out, privateDir } = workspace("http://127.0.0.1:1/");
  assert.equal((await run(["probe", "--profile", join(out, "profile.json"), "--out", out])).status, 10);
  assert.equal((await run(["finalize", "--plan", join(out, "plan.json"), "--profile", join(out, "profile.json"), "--out", out, "--private-dir", privateDir, "--commit", commit])).status, 0);
  const report = JSON.parse(readFileSync(join(out, "report.json"), "utf8"));
  assert.equal(report.verdict, "ENV-UNAVAILABLE");
  assert.equal(report.failures.length, 0);
  assert.equal(readFileSync(join(out, "conclusion.txt"), "utf8"), "failure");
  assert.match(readFileSync(join(out, "summary.md"), "utf8"), /nothing was verified/);
});

test("an available environment with no step results reports every step as not covered and stays green", async () => {
  const server = createServer((_request: IncomingMessage, response: ServerResponse) => {
    response.statusCode = 200;
    response.end("ok");
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as { port: number };
  const { out, privateDir } = workspace(`http://127.0.0.1:${port}/`);
  const probe = (await run(["probe", "--profile", join(out, "profile.json"), "--out", out])).status;
  server.close();
  assert.equal(probe, 0);
  assert.equal((await run(["finalize", "--plan", join(out, "plan.json"), "--profile", join(out, "profile.json"), "--out", out, "--private-dir", privateDir, "--commit", commit])).status, 0);
  const report = JSON.parse(readFileSync(join(out, "report.json"), "utf8"));
  assert.equal(report.verdict, "NOT-COVERED");
  assert.match(report.not_tested.declared_limits.join(" "), /first-login linking[\s\S]*identity hash/);
  assert.equal(report.workflow_conclusion, "success");
  assert.deepEqual(report.passed, []);
});

test("a secret in an artifact fails the run, withholds the evidence and keeps only paths and kinds", async () => {
  const { out, privateDir } = workspace("http://127.0.0.1:1/");
  writeFileSync(join(out, "network.jsonl"), `{"authorization":"Bearer ${"z".repeat(40)}"}\n`);
  const result = await run(["finalize", "--plan", join(out, "plan.json"), "--profile", join(out, "profile.json"), "--out", out, "--private-dir", privateDir, "--commit", commit]);
  assert.equal(result.status, 3);
  assert.equal(existsSync(join(out, "report.json")), false);
  assert.equal(existsSync(join(out, "network.jsonl")), false);
  const leaks = JSON.parse(readFileSync(join(out, "leak-findings.json"), "utf8"));
  assert.deepEqual(leaks, [{ path: "network.jsonl", kind: "bearer-token" }]);
  assert.equal(readFileSync(join(out, "conclusion.txt"), "utf8"), "failure");
});

test("an invalid report is refused", async () => {
  const { out, privateDir } = workspace("http://127.0.0.1:1/");
  const result = await run(["finalize", "--plan", join(out, "plan.json"), "--profile", join(out, "profile.json"), "--out", out, "--private-dir", privateDir, "--commit", "not-a-commit"]);
  assert.equal(result.status, 4);
  assert.match(readFileSync(join(out, "report-errors.json"), "utf8"), /40-character commit/);
});

test("usage errors exit with 2 and a missing option is reported", async () => {
  assert.equal((await run(["unknown"])).status, 2);
  const result = await run(["probe", "--out", "/tmp/x"]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /missing --profile/);
});

test("cleanup against a local Keycloak removes synthetic users, audits events and deactivates the run", async () => {
  const users = new Map<string, string>([
    ["u1", "acc-left-a"],
    ["real-1", "founder@waooaw.local"],
  ]);
  const requests: string[] = [];
  const server = createServer((request: IncomingMessage, response: ServerResponse) => {
    const url = request.url ?? "";
    requests.push(`${request.method} ${url.split("?")[0]}`);
    const send = (status: number, body: unknown = ""): void => {
      response.statusCode = status;
      response.setHeader("content-type", "application/json");
      response.end(typeof body === "string" ? body : JSON.stringify(body));
    };
    if (url.endsWith("/protocol/openid-connect/token")) return send(200, { access_token: "svc" });
    if (url.startsWith("/admin/realms/waooaw/groups?")) return send(200, [{ id: "g1", name: "synthetic" }]);
    if (url.startsWith("/admin/realms/waooaw/groups/g1/members")) return send(200, [...users].map(([id, username]) => ({ id, username })));
    const single = /^\/admin\/realms\/waooaw\/users\/([^/?]+)$/u.exec(url);
    if (single !== null && request.method === "GET") return users.has(single[1]) ? send(200, { id: single[1], username: users.get(single[1]) }) : send(404);
    if (single !== null && request.method === "DELETE") return send(users.delete(single[1]) ? 204 : 404);
    if (url.startsWith("/admin/realms/waooaw/admin-events")) return send(200, [{ resourcePath: "users/real-1", time: Date.now() }]);
    if (request.method === "DELETE" && url.startsWith("/internal/v1/acceptance/runs/")) return send(204);
    return send(500);
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as { port: number };
  const { out, privateDir } = workspace("http://127.0.0.1:1/");
  const profile = JSON.parse(readFileSync(join(out, "profile.json"), "utf8"));
  profile.origins = { web: "http://x", api: `http://127.0.0.1:${port}`, identity: `http://127.0.0.1:${port}` };
  writeFileSync(join(out, "profile.json"), JSON.stringify(profile));
  writeFileSync(join(privateDir, "run-state.json"), JSON.stringify({ runId: "run-0123456789", startedAt: new Date(Date.now() - 60_000).toISOString(), customers: { A: { userId: "u1" } }, values: {} }));
  const result = await run(["cleanup", "--profile", join(out, "profile.json"), "--out", out], {
    ACCEPTANCE_PRIVATE: privateDir,
    ACCEPTANCE_KEYCLOAK_PROVISIONER_CLIENT_SECRET: "secret-value-123",
  });
  server.close();
  assert.equal(result.status, 0);
  assert.deepEqual([...users.keys()], ["real-1"]);
  assert.ok(requests.includes("DELETE /internal/v1/acceptance/runs/run-0123456789"));
  const findings = readFileSync(join(out, "findings.jsonl"), "utf8");
  assert.match(findings, /provisioner_containment/);
  assert.doesNotMatch(findings, /synthetic_cleanup/);
  const meta = JSON.parse(readFileSync(join(out, "run-meta.json"), "utf8"));
  assert.deepEqual(meta.synthetic_volume, { customers_created: 1, customers_removed: 1, left_over: [] });
});

test("cleanup without the provisioner secret records a finding instead of silently passing", async () => {
  const { out, privateDir } = workspace("http://127.0.0.1:1/");
  const result = await run(["cleanup", "--profile", join(out, "profile.json"), "--out", out], {
    ACCEPTANCE_PRIVATE: privateDir,
    ACCEPTANCE_KEYCLOAK_PROVISIONER_CLIENT_SECRET: "",
  });
  assert.equal(result.status, 0);
  assert.match(readFileSync(join(out, "findings.jsonl"), "utf8"), /could not run/);
});
