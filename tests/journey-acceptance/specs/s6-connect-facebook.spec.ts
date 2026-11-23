// Implements: validation/acceptance/plans/slice-1-discover-to-connect.v1.yaml steps S6, S6b
// Constitutional basis: C-059 (Implementation Traceability), C-023 (Evidence First), C-063 (Data Minimisation)
import { reading, unreadable } from "../lib/claim.ts";
import { scanText } from "../lib/guards.ts";
import { assertTestUser, readGrantedPermissions } from "../lib/meta.ts";
import { pick } from "../lib/platform.ts";
import { BlockedByFlag } from "../lib/step.ts";
import { acceptanceStep, requirePassed } from "./support/acceptance.ts";
import { environment } from "./support/context.ts";
import { bodyText } from "./support/ui.ts";

interface MetaSandbox {
  app: { id: string; secret: string };
  session: { cookies: { name: string; value: string; domain: string; path: string }[] };
  userId: string;
}

function metaSandbox(): MetaSandbox {
  const id = environment("ACCEPTANCE_META_APP_ID");
  const secret = environment("ACCEPTANCE_META_APP_SECRET");
  const session = environment("ACCEPTANCE_META_TEST_USER_SESSION");
  if (id === undefined || secret === undefined || session === undefined) {
    throw new BlockedByFlag("the Meta development app or test-user session is not readable from the environment's Key Vault");
  }
  const parsed = JSON.parse(session) as MetaSandbox["session"];
  const userId = parsed.cookies.find((cookie) => cookie.name === "c_user")?.value;
  if (userId === undefined) {
    throw new BlockedByFlag("the stored Meta test-user session carries no user identifier");
  }
  return { app: { id, secret }, session: parsed, userId };
}

acceptanceStep("S6", { covers: ["AE-02-S01", "PG-16", "WC149-R007", "WC149-R008", "WC149-R010"] }, async ({ customer, run }) => {
  requirePassed(run, "S2");
  const sandbox = metaSandbox();
  await assertTestUser(run.fetchImpl, sandbox.app, sandbox.userId);
  const { page, context } = await customer("A");
  await page.goto("/connections");
  const connect = page.getByRole("button", { name: /connect facebook/i });
  if (!(await connect.isVisible({ timeout: 15_000 }).catch(() => false))) {
    throw new BlockedByFlag("Meta provider not registered in the product: the Connect Facebook control is not offered");
  }
  await context.addCookies(sandbox.session.cookies);
  await connect.click();
  const consent = page.getByRole("button", { name: /continue as|log in|allow|continue/i }).first();
  await consent.click({ timeout: 60_000 });
  await page.waitForURL((url) => url.pathname.startsWith("/connections"), { timeout: 90_000 });
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
