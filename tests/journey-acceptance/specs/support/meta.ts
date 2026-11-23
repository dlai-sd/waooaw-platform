// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 W3 Provider (Meta Graph, test user)
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import type { BrowserContext, Page } from "@playwright/test";
import { assertTestUser } from "../../lib/meta.ts";
import { BlockedByFlag } from "../../lib/step.ts";
import { environment } from "./context.ts";
import type { Run } from "./context.ts";

export interface MetaSandbox {
  app: { id: string; secret: string };
  session: { cookies: { name: string; value: string; domain: string; path: string }[] };
  userId: string;
}

export function metaSandbox(): MetaSandbox {
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

/** The test Page and its token, needed to read and delete the post a slice 2 run publishes. */
export function metaPage(): { pageId: string; token: string } {
  const pageId = environment("ACCEPTANCE_META_TEST_PAGE_ID");
  const token = environment("ACCEPTANCE_META_TEST_PAGE_TOKEN");
  if (pageId === undefined || token === undefined) {
    throw new BlockedByFlag("the Meta test Page id or token is not readable from the environment's Key Vault");
  }
  return { pageId, token };
}

/** Connects the Meta test Page through the product's own Connections screen, as a customer would. */
export async function connectFacebook(run: Run, page: Page, context: BrowserContext, sandbox: MetaSandbox): Promise<void> {
  await assertTestUser(run.fetchImpl, sandbox.app, sandbox.userId);
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
}
