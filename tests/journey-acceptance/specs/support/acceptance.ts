// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §4 Run Lifecycle step 7
// Constitutional basis: C-059 (Implementation Traceability)
import { test } from "@playwright/test";
import type { Browser, BrowserContext, Page } from "@playwright/test";
import type { PlanStep } from "../../lib/plan.ts";
import { planStep } from "../../lib/plan.ts";
import { BlockedByFlag, NotCovered, executeStep, readOutcomes, recordOutcome } from "../../lib/step.ts";
import type { StepResult } from "../../lib/step.ts";
import { getRun } from "./context.ts";
import type { Label, Run } from "./context.ts";
import { signIn } from "./ui.ts";

export interface StepContext {
  run: Run;
  step: PlanStep;
  browser: Browser;
  /** A signed-in page for the synthetic customer; provisioning problems are reported as a blocked step, not a failure. */
  customer(label: Label): Promise<{ page: Page; context: BrowserContext }>;
  /** A page with no session, for what an anonymous visitor sees. */
  visitor(): Promise<Page>;
}

export interface StepMeta {
  covers: string[];
  retries?: number;
}

/** The step needs earlier state; if that step did not pass, this one reports NOT-COVERED rather than guessing. */
export function requirePassed(run: Run, stepId: string): void {
  const earlier = readOutcomes(run.out).find((outcome) => outcome.stepId === stepId);
  if (earlier === undefined || !["PASS", "FLAKY"].includes(earlier.verdict)) {
    throw new NotCovered(`prerequisite step ${stepId} did not pass (${earlier?.verdict ?? "not run"})`);
  }
}

export function acceptanceStep(stepId: string, meta: StepMeta, body: (context: StepContext) => Promise<StepResult>): void {
  test(`${stepId} covers ${meta.covers.join(", ")}`, async ({ browser }) => {
    const run = getRun();
    const step = planStep(run.plan, stepId);
    const opened: BrowserContext[] = [];
    const context: StepContext = {
      run,
      step,
      browser,
      async customer(label) {
        const problem = await run.provision();
        if (problem !== undefined) {
          throw new BlockedByFlag(problem);
        }
        const browserContext = await run.context(browser, label);
        opened.push(browserContext);
        const page = await browserContext.newPage();
        await page.goto("/home");
        if (page.url().includes("/login") || page.url().includes("/api/auth")) {
          const customer = run.state.customers[label];
          if (customer === undefined) {
            throw new BlockedByFlag("synthetic customer is not provisioned");
          }
          await signIn(page, customer);
          await run.saveSession(browserContext, label);
        }
        return { page, context: browserContext };
      },
      async visitor() {
        const browserContext = await browser.newContext({ baseURL: run.profile.origins.web });
        opened.push(browserContext);
        return browserContext.newPage();
      },
    };
    const outcome = await executeStep(step, () => body(context), { retries: meta.retries ?? 0 });
    for (const browserContext of opened) {
      await browserContext.close();
    }
    recordOutcome(run.out, outcome);
  });
}
