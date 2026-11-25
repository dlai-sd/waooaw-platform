// Implements: validation/acceptance/plans/slice-5-navigation-alerts-oversight.v1.yaml steps S21 to S27
// Constitutional basis: C-001 (Emergency Stop), C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)
import type { Page } from "@playwright/test";
import { reading } from "../lib/claim.ts";
import { BlockedByFlag, NotCovered } from "../lib/step.ts";
import { acceptanceStep } from "./support/acceptance.ts";
import type { Run } from "./support/context.ts";
import { startTrial } from "./support/ui.ts";

const GLOBAL_MENU = ["/professionals/mine", "/marketplace", "/alerts", "/settings"];
const STAFF_LINKS = ["/admin/operations", "/admin/pricing", "/admin/providers", "/admin/azure-key-vault", "/access"];
const FIXED_SURFACES = ["overview", "plan", "decisions", "work", "results", "usage", "alerts", "rights"];

interface Projection {
  navigation?: Array<{ entryId: string; order: number; available: boolean }>;
}

async function hrefsIn(page: Page, selector: string): Promise<string[]> {
  return page.locator(`${selector} a`).evaluateAll((links) => links.map((link) => link.getAttribute("href") ?? ""));
}

async function relationshipOf(page: Page, run: Run): Promise<string> {
  const known = run.value("relationshipId");
  if (known !== undefined) {
    return known;
  }
  const relationship = (await startTrial(page, run.agent.offer)).relationshipId;
  run.setValue("relationshipId", relationship);
  return relationship;
}

acceptanceStep("S21", { covers: ["WC171-R001"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  await page.goto("/professionals/mine");
  const desktop = await hrefsIn(page, "#customer-navigation nav:not(.operations-navigation)");
  const operations = await page.getByRole("navigation", { name: "Operations" }).count();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/professionals/mine");
  const phone = await hrefsIn(page, ".bottom-navigation");
  const menuButton = await page.getByRole("button", { name: "Menu" }).count();
  const rendered = await page.content();
  const roles = await run.platform(page, "/api/platform/access/me/roles");
  const roleBody = roles.json as { administrator?: boolean; founder?: boolean } | undefined;
  return {
    reached: "L3",
    readings: {
      "S21-C1": [
        reading(
          "W1",
          { globalMenu: GLOBAL_MENU, operationsGroup: 0, phoneLinks: GLOBAL_MENU.slice(0, 3), menuButton: 1, staffLinks: [] },
          { globalMenu: desktop, operationsGroup: operations, phoneLinks: phone, menuButton, staffLinks: STAFF_LINKS.filter((href) => rendered.includes(`href="${href}"`)) },
          "the global menu, its phone form and the absence of every staff link are on screen",
        ),
        reading(
          "W2",
          { administrator: false, founder: false },
          { administrator: roleBody?.administrator === true, founder: roleBody?.founder === true },
          "the platform confirms this customer holds no staff grant",
        ),
      ],
    },
  };
});

acceptanceStep("S22", { covers: ["WC171-R002", "WC171-R004"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const relationship = await relationshipOf(page, run);
  const answer = await run.platform(page, `/api/relationships/${relationship}/workbench`);
  if (answer.status !== 200) {
    throw new BlockedByFlag(`the workbench route answered HTTP ${answer.status}`);
  }
  const projection = answer.json as Projection | undefined;
  await page.goto(`/relationships/${relationship}`);
  const surfaces = await page.locator("nav[aria-label] button[data-surface]").evaluateAll((buttons) => buttons.map((button) => button.getAttribute("data-surface") ?? ""));
  const declared = (projection?.navigation ?? []).filter((entry) => entry.available).sort((left, right) => left.order - right.order || left.entryId.localeCompare(right.entryId));
  await page.goto(`/relationships/${relationship}?surface=alerts`);
  const deepLinked = await page.locator('button[data-surface="alerts"][aria-current="page"]').count();
  return {
    reached: "L3",
    readings: {
      "S22-C1": [
        reading(
          "W1",
          { fixed: FIXED_SURFACES, declaredCount: declared.length, deepLinkOpens: 1 },
          { fixed: surfaces.slice(0, FIXED_SURFACES.length), declaredCount: surfaces.length - FIXED_SURFACES.length, deepLinkOpens: deepLinked },
          "the fixed surfaces come first in one order, the agent's own entries follow, and the deep link opens its surface",
        ),
        reading(
          "W2",
          { declaredFromPlatform: declared.length > 0 },
          { declaredFromPlatform: (projection?.navigation ?? []).length > 0 },
          "the platform's workbench projection carries the agent's declared entries the screen shows",
        ),
      ],
    },
  };
});

acceptanceStep("S23", { covers: ["PG-24", "WC171-R005", "WC171-R007"] }, async () => {
  // Owner: Platform IT Expert. The billing threshold, the spend discrepancy and the Emergency Stop confirmation reach the
  // alert policy through AlertPolicyService.RaiseAsync; until each producer calls it the harness has nothing to read.
  throw new BlockedByFlag("alert producers are not yet wired to the alert policy (owner: Platform IT Expert, WC-171 follow-up)");
});

acceptanceStep("S24", { covers: ["WC171-R006"] }, async () => {
  // Owner: Founder. The thread rate whatsapp_template_utility must be authorized on Pricing and a WhatsApp utility
  // template approved before the proactive gate may be opened, and sending stays to sandbox recipients on Demo.
  throw new BlockedByFlag("the proactive WhatsApp gate is closed: the thread rate is not authorized and no template is approved (owner: Founder)");
});

acceptanceStep("S25", { covers: ["WC171-R008", "WC171-R009"] }, async () => {
  // Owner: Founder. The harness has no operator sign-in; the Founder resolves the Demo blocked message from Operations
  // and the read-back is recorded in the calibration report.
  throw new BlockedByFlag("no operator sign-in is available to the harness (owner: Founder reads back after deployment)");
});

acceptanceStep("S26", { covers: ["WC171-R010"] }, async () => {
  // Owner: Platform IT Expert, WC-172. The spend chain is read through the billing engine, which needs a route grant that
  // the workload trust bundle cannot yet carry (WC-170 B10).
  throw new NotCovered("the billing engine spend-chain read route has no route grant yet (owner: Platform IT Expert, WC-172 trust-bundle split)");
});

acceptanceStep("S27", { covers: ["WC171-R008"] }, async () => {
  // Owner: Founder. Same operator sign-in as S25.
  throw new BlockedByFlag("no operator sign-in is available to the harness (owner: Founder reads back after deployment)");
});
