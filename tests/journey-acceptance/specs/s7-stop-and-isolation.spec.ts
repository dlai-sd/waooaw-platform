// Implements: validation/acceptance/plans/slice-1-discover-to-connect.v1.yaml steps S7, S8
// Constitutional basis: C-001 (Emergency Stop), C-059 (Implementation Traceability), AD-004 (Multi-Tenant Data Isolation)
import { reading, unreadable } from "../lib/claim.ts";
import { foreignIdentifierFindings } from "../lib/guards.ts";
import { collectIdentifiers, pick } from "../lib/platform.ts";
import { recordFindings } from "../lib/step.ts";
import { acceptanceStep, requirePassed } from "./support/acceptance.ts";
import { bodyText, startTrial } from "./support/ui.ts";


acceptanceStep("S7", { covers: ["AE-01-S10", "PG-04", "PG-15"] }, async ({ customer, run }) => {
  requirePassed(run, "S5");
  const relationshipId = run.value("relationshipId");
  if (relationshipId === undefined) {
    throw new Error("no active relationship from the earlier steps");
  }
  const { page } = await customer("A");
  await page.goto(`/relationships/${relationshipId}`);
  const evidencePath = `/api/relationships/${relationshipId}/workbench/evidence`;
  const countOf = async (): Promise<number | undefined> => {
    const response = await run.platform(page, evidencePath);
    const items = (response.json as { items?: unknown[] } | undefined)?.items;
    return Array.isArray(items) ? items.length : undefined;
  };
  const before = await countOf();
  const stop = page.getByRole("button", { name: /stop all agent work now/i });
  const reachable = await stop.isVisible({ timeout: 15_000 }).catch(() => false);
  if (reachable) {
    await stop.click();
    await page.getByText(/emergency stop confirmed/i).waitFor({ timeout: 30_000 });
  }
  const confirmed = /emergency stop confirmed/i.test(await bodyText(page));
  const after = await countOf();
  const state = pick((await run.platform(page, `/api/relationships/${relationshipId}/workbench/`)).json, ["lifecycleState", "state", "status"]);
  const releaseOffered = await page.getByRole("button", { name: /release|resume/i }).first().isVisible().catch(() => false);
  return {
    reached: "L4",
    readings: {
      "S7-C1": [
        reading("W1", { reachable: true, confirmed: true, releaseOffered: true }, { reachable, confirmed, releaseOffered }, "stop reachable and confirmed on screen; release control offered"),
        before === undefined || after === undefined || state === undefined
          ? unreadable("W2", "the workbench routes did not expose the evidence count and state needed to witness the stop")
          : !releaseOffered
            ? unreadable("W2", "the stop was recorded but no customer-reachable release control exists, so reversibility cannot be witnessed")
            : reading("W2", { evidenceAdded: true, stopped: true }, { evidenceAdded: after > before, stopped: /stop|pause|halt/i.test(String(state)) }, `evidence ${before} to ${after}, state ${String(state)}`),
      ],
    },
  };
});

acceptanceStep("S8", { covers: ["AD-004"] }, async ({ customer, run }) => {
  requirePassed(run, "S2");
  const { page: pageB } = await customer("B");
  const relationshipB = (await startTrial(pageB, run.agent.offer)).relationshipId;
  const account = await run.platform(pageB, "/api/identity/account");
  const connections = await run.platform(pageB, "/api/provider-connections");
  const learned = collectIdentifiers([account.json, connections.json, relationshipB]);
  run.foreignIds.push(relationshipB, ...learned);
  const { page } = await customer("A");
  const denied = await page.goto(`/relationships/${relationshipB}`, { waitUntil: "domcontentloaded" });
  const screen = await bodyText(page);
  const probes = [
    await run.platform(page, `/api/relationships/${relationshipB}/workbench/`),
    await run.platform(page, `/api/relationships/${relationshipB}/workbench/evidence`),
  ];
  const everything = [...run.recent, screen, ...probes.map((probe) => JSON.stringify(probe.json ?? ""))].join("\n");
  const leaks = foreignIdentifierFindings("customer A responses after learning customer B identifiers", everything, run.foreignIds);
  recordFindings(run.out, leaks);
  return {
    reached: "L5",
    readings: {
      "S8-C1": [
        reading("W1", true, (denied?.status() ?? 200) >= 400 || /forbidden|not found|not allowed|cannot/i.test(screen), `the page for customer B's relationship answered HTTP ${denied?.status() ?? "unknown"}`),
        reading("W2", { refused: true, leaked: 0 }, { refused: probes.every((probe) => [401, 403, 404].includes(probe.status)), leaked: leaks.length }, `route statuses ${probes.map((probe) => probe.status).join(", ")}; ${leaks.length} customer B identifiers seen`),
      ],
    },
  };
});
