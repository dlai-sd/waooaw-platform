// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §4 Run Lifecycle
// Constitutional basis: C-059 (Implementation Traceability), C-049 (Honest Limitation)
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { loadCompiledPlan, stepIdentifiers } from "./lib/plan.ts";
import { cleanupSyntheticUsers } from "./lib/cleanup.ts";
import { Provisioner } from "./lib/keycloak.ts";
import { deactivateRun } from "./lib/marker.ts";
import { probeEnvironment } from "./lib/probe.ts";
import type { ProbeOutcome } from "./lib/probe.ts";
import { readLiterals } from "./lib/private-store.ts";
import type { FetchLike } from "./lib/razorpay.ts";
import { buildReport, renderSummary, validateReport } from "./lib/report.ts";
import { scanArtifacts, withholdArtifacts } from "./lib/secret-scan.ts";
import { readFindings, readOutcomes, recordFindings } from "./lib/step.ts";

interface Profile {
  environment: string;
  probes: { name: string; url: string }[];
  probe_timeout_ms: number;
  profile_digest: string;
}

function option(args: string[], name: string): string {
  const index = args.indexOf(`--${name}`);
  if (index === -1 || index + 1 >= args.length) {
    throw new Error(`missing --${name}`);
  }
  return args[index + 1];
}

function readJson<T>(path: string, fallback?: T): T {
  if (!existsSync(path)) {
    if (fallback !== undefined) {
      return fallback;
    }
    throw new Error(`missing file ${path}`);
  }
  return JSON.parse(readFileSync(path, "utf8")) as T;
}

async function probe(args: string[]): Promise<number> {
  const profile = readJson<Profile>(option(args, "profile"));
  const out = option(args, "out");
  mkdirSync(out, { recursive: true });
  const outcome = await probeEnvironment(profile.probes, { timeoutMs: profile.probe_timeout_ms });
  writeFileSync(join(out, "probe.json"), JSON.stringify(outcome, null, 2));
  return outcome.available ? 0 : 10;
}

function finalize(args: string[]): number {
  const out = option(args, "out");
  const privateDir = option(args, "private-dir");
  const { plan, planDigest, liveScope } = loadCompiledPlan(option(args, "plan"));
  const profile = readJson<Profile>(option(args, "profile"));
  const meta = readJson<{
    services: { name: string; image: string }[];
    provider_mode_findings: string[];
    synthetic_volume: { customers_created: number; customers_removed: number; left_over: string[] };
    started_at: string;
  }>(join(out, "run-meta.json"), {
    services: [],
    provider_mode_findings: [],
    synthetic_volume: { customers_created: 0, customers_removed: 0, left_over: [] },
    started_at: new Date().toISOString(),
  });
  const probeOutcome = existsSync(join(out, "probe.json")) ? readJson<ProbeOutcome>(join(out, "probe.json")) : undefined;
  const denominator = [...new Set([...plan.steps.flatMap(stepIdentifiers), ...liveScope])];
  const report = buildReport({
    environment: profile.environment,
    plan,
    planDigest,
    profileDigest: profile.profile_digest,
    commit: option(args, "commit"),
    services: meta.services,
    startedAt: meta.started_at,
    finishedAt: new Date().toISOString(),
    outcomes: readOutcomes(out),
    findings: readFindings(out),
    probe: probeOutcome,
    providerModeFindings: meta.provider_mode_findings,
    syntheticVolume: meta.synthetic_volume,
    denominator,
    declaredLimits: [
      "Google and Facebook first-login linking is not exercised by local synthetic users (NOT-COVERED).",
      "The trial verified-identity hash binding is not exercised because synthetic users carry no such claim (NOT-COVERED).",
      "Playwright trace and video are not captured in v1 because they cannot be masked reliably; screenshots are not captured either; a redacted network log is kept.",
    ],
  });
  const errors = validateReport(report);
  if (errors.length > 0) {
    writeFileSync(join(out, "report-errors.json"), JSON.stringify(errors, null, 2));
    return 4;
  }
  writeFileSync(join(out, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(out, "summary.md"), renderSummary(report));
  const leaks = scanArtifacts(out, [], readLiterals(privateDir));
  if (leaks.length > 0) {
    withholdArtifacts(out);
    writeFileSync(join(out, "leak-findings.json"), JSON.stringify(leaks, null, 2));
    writeFileSync(join(out, "conclusion.txt"), "failure");
    return 3;
  }
  writeFileSync(join(out, "conclusion.txt"), report.workflow_conclusion);
  return 0;
}

async function cleanup(args: string[]): Promise<number> {
  const out = option(args, "out");
  const profile = readJson<
    Profile & { origins: { api: string; identity: string }; keycloak: { realm: string; username_prefix: string; email_domain: string; synthetic_group: string } }
  >(option(args, "profile"));
  const privateDir = process.env.ACCEPTANCE_PRIVATE ?? "/private";
  const secret = process.env.ACCEPTANCE_KEYCLOAK_PROVISIONER_CLIENT_SECRET;
  const stateFile = join(privateDir, "run-state.json");
  const state = existsSync(stateFile)
    ? (JSON.parse(readFileSync(stateFile, "utf8")) as { runId: string; startedAt: string; customers: Record<string, { userId: string }> })
    : undefined;
  const metaFile = join(out, "run-meta.json");
  const meta = readJson<{ synthetic_volume: { customers_created: number; customers_removed: number; left_over: string[] } } & Record<string, unknown>>(metaFile, {
    synthetic_volume: { customers_created: 0, customers_removed: 0, left_over: [] },
  });
  if (secret === undefined || secret === "") {
    recordFindings(out, [{ guard: "synthetic_cleanup", where: "keycloak", detail: "the provisioner secret is not readable, so cleanup could not run" }]);
    return 0;
  }
  const provisioner = new Provisioner(
    {
      identityOrigin: profile.origins.identity,
      realm: profile.keycloak.realm,
      clientId: "waooaw-acceptance-provisioner",
      clientSecret: secret,
      usernamePrefix: profile.keycloak.username_prefix,
      emailDomain: profile.keycloak.email_domain,
      group: profile.keycloak.synthetic_group,
    },
    (url, init) => fetch(url, init) as ReturnType<FetchLike>,
  );
  const owned = Object.values(state?.customers ?? {}).map((customer) => customer.userId);
  const result = await cleanupSyntheticUsers(provisioner, owned, state?.startedAt ?? new Date(Date.now() - 3_600_000).toISOString());
  if (state !== undefined) {
    await deactivateRun((url, init) => fetch(url, init) as ReturnType<FetchLike>, profile.origins.api, await provisioner.serviceToken(), state.runId).catch((error: unknown) => {
      recordFindings(out, [{ guard: "synthetic_cleanup", where: "business platform", detail: `the run could not be deactivated: ${error instanceof Error ? error.message : String(error)}` }]);
    });
  }
  recordFindings(out, result.findings);
  writeFileSync(
    metaFile,
    JSON.stringify({
      ...meta,
      synthetic_volume: { customers_created: owned.length, customers_removed: owned.length - result.leftOver.length, left_over: result.leftOver },
    }),
  );
  return 0;
}

const [command, ...rest] = process.argv.slice(2);
if (command === "probe") {
  process.exitCode = await probe(rest);
} else if (command === "finalize") {
  process.exitCode = finalize(rest);
} else if (command === "cleanup") {
  process.exitCode = await cleanup(rest);
} else {
  console.error("usage: run.ts probe|finalize|cleanup ...");
  process.exitCode = 2;
}
