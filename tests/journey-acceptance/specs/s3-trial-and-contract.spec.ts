// Implements: validation/acceptance/plans/slice-1-discover-to-connect.v1.yaml steps S3, S3b, S4
// Constitutional basis: C-059 (Implementation Traceability), C-023 (Evidence First)
import type { Page } from "@playwright/test";
import { reading, unreadable } from "../lib/claim.ts";
import { pick } from "../lib/platform.ts";
import { acceptanceStep, requirePassed } from "./support/acceptance.ts";
import type { Run } from "./support/context.ts";
import { bodyText, openProfessionalDisclosure, startTrial } from "./support/ui.ts";


async function relationshipState(run: Run, page: Page, relationshipId: string): Promise<{ state?: string; evidenceCount?: number }> {
  const summary = await run.platform(page, `/api/relationships/${relationshipId}/workbench/`);
  const evidence = await run.platform(page, `/api/relationships/${relationshipId}/workbench/evidence`);
  const state = summary.status === 200 ? pick(summary.json, ["lifecycleState", "state", "status"]) : undefined;
  const items = evidence.status === 200 ? pick(evidence.json, ["count", "total"]) : undefined;
  const listed = evidence.status === 200 && Array.isArray((evidence.json as { items?: unknown[] } | undefined)?.items)
    ? ((evidence.json as { items: unknown[] }).items.length)
    : undefined;
  return { state: state === undefined ? undefined : String(state), evidenceCount: typeof items === "number" ? items : listed };
}

acceptanceStep("S3", { covers: ["AE-01-S05", "PG-08", "WC107-R010", "WC107-R011", "WC107-R015"] }, async ({ customer, run }) => {
  requirePassed(run, "S2");
  const { page } = await customer("A");
  const relationshipId = (await startTrial(page, run.agent.offer)).relationshipId;
  run.setValue("relationshipId", relationshipId);
  const screen = await bodyText(page);
  const platform = await relationshipState(run, page, relationshipId);
  const trialOnScreen = /trial/i.test(screen) && /rights|limits|control/i.test(screen);
  return {
    reached: "L4",
    readings: {
      "S3-C1": [
        reading("W1", true, trialOnScreen, "trial and the rights are shown after the page reloads from the platform"),
        platform.state === undefined
          ? unreadable("W2", "the workbench route did not expose a lifecycle state for the relationship")
          : reading("W2", true, /trial/i.test(platform.state) && (platform.evidenceCount ?? 0) > 0, `platform state ${platform.state}, ${platform.evidenceCount ?? "unknown"} evidence entries`),
      ],
    },
  };
});

acceptanceStep("S3b", { covers: ["PG-08", "WC107-R011"] }, async ({ customer, run }) => {
  requirePassed(run, "S3");
  const relationshipId = run.value("relationshipId");
  const { page } = await customer("A");
  await openProfessionalDisclosure(page, run.agent.offer);
  const trialOffered = await page.getByRole("button", { name: /review free .*trial/i }).isVisible();
  const refusal = /already|one trial|not available|no longer/i.test(await bodyText(page));
  const platform = relationshipId === undefined ? undefined : await relationshipState(run, page, relationshipId);
  return {
    reached: "L5",
    readings: {
      "S3b-C1": [
        reading("W1", true, !trialOffered || refusal, trialOffered ? "a second trial is still offered" : "no second trial is offered"),
        platform?.state === undefined
          ? unreadable("W2", "the workbench route did not expose the relationship state")
          : reading("W2", true, /trial/i.test(platform.state), `relationship remains ${platform.state}`),
      ],
    },
  };
});

acceptanceStep("S4", { covers: ["AE-01-S06", "AE-01-S07", "PG-10"] }, async ({ customer, run }) => {
  requirePassed(run, "S3");
  const relationshipId = run.value("relationshipId");
  if (relationshipId === undefined) {
    throw new Error("no relationship from the trial step");
  }
  const { page } = await customer("A");
  await page.goto(`/relationships/${relationshipId}`);
  const before = await relationshipState(run, page, relationshipId);
  await page.getByRole("button", { name: /accept exact monthly contract/i }).click();
  await page.waitForLoadState("networkidle");
  const screen = await bodyText(page);
  const accepted = !(await page.getByRole("button", { name: /accept exact monthly contract/i }).isVisible()) && /accepted|contract/i.test(screen);
  const state = await relationshipState(run, page, relationshipId);
  const added = (state.evidenceCount ?? 0) - (before.evidenceCount ?? 0);
  return {
    reached: "L4",
    readings: {
      "S4-C1": [
        reading("W1", true, accepted, "the accept control is gone and the contract shows as accepted"),
        state.state === undefined || state.evidenceCount === undefined
          ? unreadable("W2", "the workbench routes did not expose the evidence count needed to witness acceptance")
          : reading("W2", true, added > 0, `${added} evidence entries recorded by the acceptance`),
      ],
    },
  };
});
