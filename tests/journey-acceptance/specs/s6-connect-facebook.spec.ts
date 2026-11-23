// Implements: validation/acceptance/plans/slice-1-discover-to-connect.v1.yaml steps S6, S6b
// Constitutional basis: C-059 (Implementation Traceability), C-023 (Evidence First), C-063 (Data Minimisation)
import { reading, unreadable } from "../lib/claim.ts";
import { scanText } from "../lib/guards.ts";
import { readGrantedPermissions } from "../lib/meta.ts";
import { pick } from "../lib/platform.ts";
import { acceptanceStep, requirePassed } from "./support/acceptance.ts";
import { connectFacebook, metaSandbox } from "./support/meta.ts";
import { bodyText } from "./support/ui.ts";

acceptanceStep("S6", { covers: ["AE-02-S01", "PG-16", "WC149-R007", "WC149-R008", "WC149-R010"] }, async ({ customer, run }) => {
  requirePassed(run, "S2");
  const sandbox = metaSandbox();
  const { page, context } = await customer("A");
  await connectFacebook(run, page, context, sandbox);
  const screen = await bodyText(page);
  const listed = await run.platform(page, "/api/provider-connections");
  const first = Array.isArray(listed.json) ? (listed.json[0] as Record<string, unknown> | undefined) : undefined;
  const status = first === undefined ? undefined : String(pick(first, ["status"]));
  const scopes = Array.isArray(first?.scopes) ? (first.scopes as string[]).slice().sort() : [];
  const noToken = scanText(JSON.stringify(listed.json ?? {})).length === 0 && !/token/i.test(Object.keys(first ?? {}).join(","));
  const graph = await readGrantedPermissions(run.fetchImpl, sandbox.app, sandbox.userId);
  return {
    reached: "L4",
    readings: {
      "S6-C1": [
        reading("W1", true, /connected/i.test(screen), "the card shows Connected"),
        first === undefined
          ? unreadable("W2", "the provider-connections route returned no connection")
          : reading("W2", { status: "CONNECTED", noToken: true, scopesPresent: true }, { status, noToken, scopesPresent: scopes.length > 0 }, "status, scopes and absence of any token in the response"),
        reading("W3", true, scopes.length > 0 && scopes.every((scope) => graph.granted.includes(scope)), `the test user has granted ${graph.granted.join(", ")}`),
      ],
    },
  };
});

acceptanceStep("S6b", { covers: ["PG-16", "WC149-R008"] }, async ({ customer, run }) => {
  requirePassed(run, "S6");
  const { page } = await customer("A");
  await page.goto("/connections");
  await page.getByRole("button", { name: /^revoke/i }).first().click();
  await page.getByRole("button", { name: /^(revoke|confirm)/i }).last().click();
  await page.waitForLoadState("networkidle");
  const screen = await bodyText(page);
  const listed = await run.platform(page, "/api/provider-connections");
  const first = Array.isArray(listed.json) ? (listed.json[0] as Record<string, unknown> | undefined) : undefined;
  const status = first === undefined ? "none" : String(pick(first, ["status"]));
  return {
    reached: "L5",
    readings: {
      "S6b-C1": [
        reading("W1", true, /revoked/i.test(screen), "the card or notice shows Revoked"),
        reading("W2", true, status === "REVOKED" || status === "none", `connection list status ${status}`),
        // Revoke deletes the stored secret version inside Business Platform custody, which the harness must not read (architecture section 5).
        // The user's grant on Facebook remains until the user removes it there, so Graph cannot witness the deletion.
        unreadable("W3", "Graph cannot show that WAOOAW deleted its stored access; custody is deliberately unreadable by the harness"),
      ],
    },
  };
});
