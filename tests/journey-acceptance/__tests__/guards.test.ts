// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §9 F7, F8, F9
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import {
  Guards,
  accessibilityFindings,
  emergencyStopFindings,
  foreignIdentifierFindings,
  personalDataFindings,
  scanText,
  secretFindings,
} from "../lib/guards.ts";
import { readLiterals, registerLiteral } from "../lib/private-store.ts";
import { scanArtifacts, withholdArtifacts } from "../lib/secret-scan.ts";

const JWT = ["eyJhbGciOiJSUzI1NiJ9", "eyJzdWIiOiIxMjM0NTY3ODkwIn0", "c2lnbmF0dXJlLXZhbHVl"].join(".");

test("a seeded token is detected and its value is never copied into the finding", () => {
  const findings = secretFindings("GET /api/relationships", `{"note":"${JWT}"}`);
  assert.equal(findings.length, 1);
  assert.equal(findings[0].guard, "secret_or_token_pattern");
  assert.ok(!JSON.stringify(findings).includes(JWT));
  assert.deepEqual(scanText("Bearer abcdefghijklmnopqrstuvwxyz0123"), ["bearer-token"]);
  assert.deepEqual(scanText(`{"refresh_token":"${"abcdefghij".repeat(2)}"}`), ["token-field"]);
  assert.deepEqual(scanText("nothing sensitive here"), []);
});

test("a seeded customer B identifier in a customer A response is detected", () => {
  const findings = foreignIdentifierFindings("GET /api/relationships/rel-1", "id: 7f3a9c2e-b", ["7f3a9c2e-b", "ab"]);
  assert.equal(findings.length, 1);
  assert.equal(findings[0].guard, "foreign_tenant_identifier");
  assert.ok(!findings[0].detail.includes("7f3a9c2e-b"));
  assert.deepEqual(foreignIdentifierFindings("x", "clean", ["7f3a9c2e-b"]), []);
});

test("personal data outside the synthetic and product domains is a finding", () => {
  const allowed = ["synthetic.waooaw.test", "waooaw.com"];
  assert.deepEqual(personalDataFindings("p", "a@x.synthetic.waooaw.test b@waooaw.com", allowed), []);
  assert.equal(personalDataFindings("p", "mail real@gmail.com", allowed).length, 1);
  assert.equal(personalDataFindings("p", "call +919812345678 now", allowed).length, 1);
});

test("a seeded accessibility violation and a missing Emergency Stop are detected", () => {
  const findings = accessibilityFindings("/", [
    { id: "color-contrast", impact: "serious", nodes: [{}, {}] },
    { id: "region", impact: "moderate", nodes: [{}] },
    { id: "image-alt", impact: "critical" },
  ]);
  assert.equal(findings.length, 2);
  assert.match(findings[0].detail, /2 node/);
  assert.equal(emergencyStopFindings("/relationships/1", { present: true, visible: true }).length, 0);
  assert.equal(emergencyStopFindings("/relationships/1", { present: true, visible: false }).length, 1);
  assert.equal(emergencyStopFindings("/relationships/1", { present: false, visible: false }).length, 1);
});

test("the always-on guard observes every page and response", () => {
  const foreign = ["tenant-b-0001"];
  const guards = new Guards({ foreignIdentifiers: () => foreign, allowedEmailDomains: ["synthetic.waooaw.test"] });
  guards.observe("page /", "all clear");
  guards.observe("response /api/x", `${JWT} tenant-b-0001 someone@gmail.com`);
  guards.record(accessibilityFindings("/", [{ id: "label", impact: "serious" }]));
  assert.deepEqual(
    guards.findings().map((finding) => finding.guard),
    ["secret_or_token_pattern", "foreign_tenant_identifier", "personal_data_leakage", "wcag_2_1_aa"],
  );
});

test("the pre-upload scan finds seeded secrets and run-generated literals, then withholds the artifact", () => {
  const directory = mkdtempSync(join(tmpdir(), "ja-scan-"));
  mkdirSync(join(directory, "network"));
  writeFileSync(join(directory, "report.json"), "{}");
  writeFileSync(join(directory, "network", "har.json"), `{"authorization":"Bearer ${"a".repeat(30)}"}`);
  writeFileSync(join(directory, "note.txt"), "password was Zx9-generated-pw");
  const findings = scanArtifacts(directory, [], ["Zx9-generated-pw", "short"]);
  assert.deepEqual(
    findings.map((finding) => `${finding.path}:${finding.kind}`).sort(),
    ["network/har.json:bearer-token", "note.txt:run-secret-literal"],
  );
  assert.ok(!JSON.stringify(findings).includes("Zx9-generated-pw"));
  assert.deepEqual(scanArtifacts(mkdtempSync(join(tmpdir(), "ja-clean-")), [], []), []);
  withholdArtifacts(directory, []);
  assert.deepEqual(readdirSync(directory), []);
});

test("run literals are kept in a private directory and read back", () => {
  const privateDir = mkdtempSync(join(tmpdir(), "ja-private-"));
  assert.deepEqual(readLiterals(privateDir), []);
  registerLiteral(privateDir, "first-secret-value");
  registerLiteral(privateDir, "second-secret-value");
  assert.deepEqual(readLiterals(privateDir), ["first-secret-value", "second-secret-value"]);
});
