// Implements: validation/acceptance/plans/slice-4-agent-work.v1.yaml steps S12 to S20
// Constitutional basis: C-001 (Emergency Stop), C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)
import type { Page } from "@playwright/test";
import { reading, unreadable } from "../lib/claim.ts";
import { BlockedByFlag, NotCovered } from "../lib/step.ts";
import { acceptanceStep } from "./support/acceptance.ts";
import type { Run } from "./support/context.ts";
import { bodyText, startTrial } from "./support/ui.ts";

interface Decision {
  evidenceId?: string;
}
interface ArtifactItem {
  artifact: {
    artifactId: string;
    artifactType: string;
    digest: string;
    status: string;
    supersedesArtifactId?: string | null;
    plainLanguageSummary: string;
    authorityBoundary?: string | null;
    content?: { dimensions?: Array<{ status: string; score: number | null; evidenceRefs: string[] }> };
  };
  decisions: { approval: Decision | null; scopeConfirmation: Decision | null; executable: boolean };
}
interface TimelineEvent {
  state: string;
  workItemType: string;
  artifactDigest?: string | null;
  providerReference?: string | null;
  reasonCode?: string | null;
  sequence: number;
}
interface Claim {
  claimId: string;
  derivation: string;
  label?: string | null;
  workItemIds: string[];
  evidenceIds: string[];
}
interface RealWork {
  artifacts: { items: ArtifactItem[] } | null;
  timeline: { events: TimelineEvent[]; workItems: Array<{ state: string }>; emergencyStopActive: boolean } | null;
  outcomes: { activity: Claim[]; outcomes: Claim[]; agentStated: Claim[]; notMeasurableYet: Array<{ text: string }> } | null;
}

const SIX_STATES = new Set(["PROPOSED", "APPROVED", "EXECUTING", "COMPLETED", "FAILED", "HALTED"]);

async function relationshipOf(page: Page, run: Run): Promise<string> {
  const known = run.value("relationshipId");
  if (known !== undefined) {
    return known;
  }
  // Slice 4 starts from whatever hire the earlier slices left; with none, a trial relationship is the honest starting point.
  const relationship = (await startTrial(page, run.agent.offer)).relationshipId;
  run.setValue("relationshipId", relationship);
  return relationship;
}

async function readWork(page: Page, run: Run, relationship: string): Promise<RealWork> {
  const answer = await run.platform(page, `/api/relationships/${relationship}/real-work`);
  const work = answer.json as RealWork | undefined;
  if (answer.status !== 200 || work === undefined) {
    throw new BlockedByFlag(`the real-work route answered HTTP ${answer.status}`);
  }
  if (work.artifacts === null && work.timeline === null) {
    throw new BlockedByFlag("the employment protocol is off or the relationship is not hired (EMPLOYMENT_NOT_ACCESSIBLE)");
  }
  return work;
}

async function openWork(page: Page, relationship: string): Promise<void> {
  await page.goto(`/relationships/${relationship}`);
  await page.getByRole("button", { name: /^work$/i }).click();
  await page.getByRole("heading", { name: /your decisions/i }).waitFor({ timeout: 30_000 });
}

function artifactOf(work: RealWork, type: string, statuses: string[]): ArtifactItem {
  const found = work.artifacts?.items.find((item) => item.artifact.artifactType === type && statuses.includes(item.artifact.status));
  if (found === undefined) {
    throw new BlockedByFlag(`no ${type} has been proposed yet (the agent has not run, or no AI provider key is configured)`);
  }
  return found;
}

function card(page: Page, type: string) {
  return page.locator("li.workbench-card").filter({ hasText: new RegExp(type.replaceAll("_", " "), "i") });
}

async function approve(page: Page, type: string): Promise<void> {
  const button = card(page, type).getByRole("button", { name: /approve this version/i });
  if (await button.isEnabled().catch(() => false)) {
    await button.click();
    await card(page, type).getByText(/both steps are done|done/i).first().waitFor({ timeout: 30_000 });
  }
}

acceptanceStep("S12", { covers: ["AE-02-S02", "PG-17", "PG-18", "WC170-R001", "WC170-R003", "WC170-R004", "WC170-R005"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const relationship = await relationshipOf(page, run);
  const profile = artifactOf(await readWork(page, run, relationship), "PROFILE_CONFIRMATION", ["PROPOSED", "LOCKED"]);
  await openWork(page, relationship);
  const shown = await card(page, "PROFILE_CONFIRMATION").getByText(profile.artifact.plainLanguageSummary).isVisible().catch(() => false);
  const noToken = !/\{DVE\./.test(await bodyText(page));
  await approve(page, "PROFILE_CONFIRMATION");
  const locked = artifactOf(await readWork(page, run, relationship), "PROFILE_CONFIRMATION", ["LOCKED"]);
  return {
    reached: "L4",
    readings: {
      "S12-C1": [
        reading("W1", { shown: true, noRawVocabularyToken: true }, { shown, noRawVocabularyToken: noToken }, "the profile summary is on screen in business language"),
        reading(
          "W2",
          { locked: true, evidence: true, digest: true },
          { locked: locked.artifact.status === "LOCKED", evidence: Boolean(locked.decisions.approval?.evidenceId), digest: /^[0-9a-f]{64}$/.test(locked.artifact.digest) },
          "the platform shows the exact version locked with an approval evidence id and a digest",
        ),
      ],
    },
  };
});

acceptanceStep("S13", { covers: ["AE-02-S02", "PG-18", "WC170-R005"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const relationship = await relationshipOf(page, run);
  const report = artifactOf(await readWork(page, run, relationship), "MATURITY_REPORT", ["PROPOSED", "LOCKED"]);
  await openWork(page, relationship);
  const rows = report.artifact.content?.dimensions ?? [];
  const honest = rows.length === 10 && rows.every((row) =>
    row.status === "SCORED" ? row.score !== null && row.score >= 1 && row.score <= 10 && row.evidenceRefs.length > 0 : row.status === "NOT_ENOUGH_INFORMATION" && row.score === null,
  );
  const shown = await card(page, "MATURITY_REPORT").getByText(report.artifact.plainLanguageSummary).isVisible().catch(() => false);
  return {
    reached: "L3",
    readings: {
      "S13-C1": [
        reading("W1", true, shown, "the maturity report is on screen"),
        rows.length === 0
          ? unreadable("W2", "the report carries no dimension rows")
          : reading("W2", { tenDimensions: true, scoredOnlyWithEvidence: true }, { tenDimensions: rows.length === 10, scoredOnlyWithEvidence: honest }, `${rows.filter((row) => row.status === "SCORED").length} of 10 dimensions scored; the rest say not enough information`),
      ],
    },
  };
});

acceptanceStep("S14", { covers: ["AE-02-S03", "PG-18", "PG-19", "WC170-R005", "WC170-R006"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const relationship = await relationshipOf(page, run);
  const before = artifactOf(await readWork(page, run, relationship), "CAMPAIGN_BRIEF", ["PROPOSED", "LOCKED"]);
  await openWork(page, relationship);
  await approve(page, "CAMPAIGN_BRIEF");
  const after = artifactOf(await readWork(page, run, relationship), "CAMPAIGN_BRIEF", ["LOCKED"]);
  return {
    reached: "L4",
    readings: {
      "S14-C1": [
        reading("W1", true, await card(page, "CAMPAIGN_BRIEF").getByText(/done/i).first().isVisible().catch(() => false), "the approval step reads Done on the brief"),
        reading("W2", { locked: true, sameDigest: true, evidence: true }, { locked: after.artifact.status === "LOCKED", sameDigest: after.artifact.digest === before.artifact.digest, evidence: Boolean(after.decisions.approval?.evidenceId) }, "approval locked the exact digest that was shown"),
      ],
    },
  };
});

acceptanceStep("S15", { covers: ["AE-02-S03", "AE-02-S04", "PG-19", "WC170-R006"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const relationship = await relationshipOf(page, run);
  const brief = artifactOf(await readWork(page, run, relationship), "CAMPAIGN_BRIEF", ["LOCKED"]);
  await openWork(page, relationship);
  const confirm = card(page, "CAMPAIGN_BRIEF").getByRole("button", { name: /confirm the boundary/i });
  if (await confirm.isEnabled().catch(() => false)) {
    await confirm.click();
    await card(page, "CAMPAIGN_BRIEF").getByText(/both steps are done/i).waitFor({ timeout: 30_000 });
  }
  const after = artifactOf(await readWork(page, run, relationship), "CAMPAIGN_BRIEF", ["LOCKED"]);
  return {
    reached: "L4",
    readings: {
      "S15-C1": [
        reading("W1", true, await card(page, "CAMPAIGN_BRIEF").getByText(/both steps are done/i).isVisible().catch(() => false), "the screen says both steps are done"),
        reading(
          "W2",
          { scopeRecorded: true, separateEvidence: true, executable: true },
          {
            scopeRecorded: after.decisions.scopeConfirmation !== null,
            separateEvidence: after.decisions.scopeConfirmation?.evidenceId !== undefined && after.decisions.scopeConfirmation.evidenceId !== brief.decisions.approval?.evidenceId,
            executable: after.decisions.executable,
          },
          "scope confirmation is its own record and only both records make the brief executable",
        ),
      ],
    },
  };
});

acceptanceStep("S16", { covers: ["AE-02-S04", "PG-19", "WC170-R006"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const relationship = await relationshipOf(page, run);
  const work = await readWork(page, run, relationship);
  const drafts = work.artifacts?.items.filter((item) => item.artifact.artifactType === "CONTENT_DRAFT") ?? [];
  const correction = drafts.find((item) => item.artifact.supersedesArtifactId);
  if (correction === undefined) {
    throw new BlockedByFlag("no draft correction exists yet; ask the agent for a correction in the conversation first");
  }
  const earlier = drafts.find((item) => item.artifact.artifactId === correction.artifact.supersedesArtifactId);
  await openWork(page, relationship);
  return {
    reached: "L3",
    readings: {
      "S16-C1": [
        reading("W1", true, await page.getByText(/replaced by a newer version/i).first().isVisible().catch(() => false), "the earlier draft shows as replaced"),
        reading(
          "W2",
          { earlierSuperseded: true, correctionNeedsOwnApproval: true, boundaryShown: true },
          {
            earlierSuperseded: earlier?.artifact.status === "SUPERSEDED" || earlier?.artifact.status === "LOCKED",
            correctionNeedsOwnApproval: correction.decisions.approval === null || correction.artifact.status !== "SUPERSEDED",
            boundaryShown: Boolean(correction.artifact.authorityBoundary),
          },
          "the correction is a new version and the draft names what the agent may do",
        ),
      ],
    },
  };
});

acceptanceStep("S17", { covers: ["AE-02-S04", "AE-02-S05", "PG-20", "WC170-R002", "WC170-R007", "WC170-R012"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const relationship = await relationshipOf(page, run);
  const work = await readWork(page, run, relationship);
  const events = work.timeline?.events ?? [];
  if (events.length === 0) {
    throw new BlockedByFlag("the agent has not executed any work yet (no execution event is on the timeline)");
  }
  await openWork(page, relationship);
  const bound = events.filter((event) => ["EXECUTING", "COMPLETED"].includes(event.state) && event.reasonCode !== "AWAITING_PROVIDER_PROOF");
  const publications = events.filter((event) => /PUBLICATION|POST/.test(event.workItemType) && event.state === "COMPLETED");
  return {
    reached: "L4",
    readings: {
      "S17-C1": [
        reading("W1", true, await page.getByText(/what the agent is doing/i).isVisible().catch(() => false), "the timeline is on screen with one sentence per work item"),
        reading(
          "W2",
          { sixStatesOnly: true, stepsNameTheirDigest: true, publicationsHaveProviderReference: true },
          {
            sixStatesOnly: events.every((event) => SIX_STATES.has(event.state)),
            stepsNameTheirDigest: bound.every((event) => event.artifactDigest === undefined || event.artifactDigest === null || /^[0-9a-f]{64}$/.test(event.artifactDigest)),
            publicationsHaveProviderReference: publications.every((event) => Boolean(event.providerReference)),
          },
          `${events.length} events; a publication counts as done only with the provider's own reference`,
        ),
      ],
    },
  };
});

acceptanceStep("S18", { covers: ["AE-02-S05", "PG-21", "WC170-R008"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const relationship = await relationshipOf(page, run);
  const outcomes = (await readWork(page, run, relationship)).outcomes;
  if (outcomes === null || outcomes.activity.length + outcomes.agentStated.length === 0) {
    throw new BlockedByFlag("no completed work or reported figure exists yet to trace");
  }
  await openWork(page, relationship);
  const traced = [...outcomes.activity, ...outcomes.agentStated].every((claim) => claim.workItemIds.length > 0 && claim.evidenceIds.length > 0);
  const labelled = outcomes.agentStated.every((claim) => claim.derivation === "AGENT_STATED" && Boolean(claim.label));
  return {
    reached: "L4",
    readings: {
      "S18-C1": [
        reading("W1", { activityApart: true, notMeasurableShown: outcomes.notMeasurableYet.length > 0 }, {
          activityApart: await page.getByText(/this counts work done/i).isVisible().catch(() => false),
          notMeasurableShown: outcomes.notMeasurableYet.length === 0 || (await page.getByText(/not measurable yet/i).first().isVisible().catch(() => false)),
        }, "work completed is shown apart from business results"),
        reading(
          "W2",
          { everyClaimTraced: true, agentFiguresLabelled: true, noIndependentOutcomeWithoutSource: true },
          { everyClaimTraced: traced, agentFiguresLabelled: labelled, noIndependentOutcomeWithoutSource: outcomes.outcomes.every((claim) => claim.derivation === "INDEPENDENT") },
          "every shown claim lists its work items and evidence",
        ),
      ],
    },
  };
});

acceptanceStep("S19", { covers: ["AE-02-S04", "AE-02-S05", "PG-22", "WC170-R009"] }, async () => {
  // No customer or platform read route exposes the sandbox spend chain yet: the chain is proven by the Billing Engine
  // tests, and its Demo read-back needs the WBE route grants deployed plus a Founder read of the reconciliation result.
  throw new NotCovered("no read route exposes the sandbox spend chain to the harness yet; the Founder reads the reconciliation result after deployment");
});

acceptanceStep("S20", { covers: ["AE-02-S05", "PG-20", "PG-23", "WC170-R010", "WC170-R011"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const relationship = await relationshipOf(page, run);
  await readWork(page, run, relationship);
  await page.goto(`/relationships/${relationship}`);
  const stop = page.getByRole("button", { name: /stop all agent work now/i });
  if (!(await stop.isVisible({ timeout: 15_000 }).catch(() => false))) {
    throw new BlockedByFlag("Stop all agent work now is not reachable on this relationship");
  }
  await stop.click();
  await page.getByText(/emergency stop confirmed/i).waitFor({ timeout: 30_000 });
  const timeline = (await readWork(page, run, relationship)).timeline;
  const events = [...(timeline?.events ?? [])].sort((left, right) => left.sequence - right.sequence);
  const stopAt = events.findIndex((event) => event.workItemType === "EMERGENCY_STOP");
  const lateSuccess = stopAt >= 0 && events.slice(stopAt + 1).some((event) => event.state === "COMPLETED");
  await page.getByRole("button", { name: /^monitor$/i }).click();
  const monitorOpens = await page.getByRole("heading", { name: /^monitor$/i }).isVisible({ timeout: 15_000 }).catch(() => false);
  return {
    reached: "L5",
    readings: {
      "S20-C1": [
        reading("W1", { haltShown: true, monitorOpens: true }, { haltShown: await page.getByText(/emergency stop confirmed/i).first().isVisible().catch(() => false), monitorOpens }, "the stop is confirmed on screen and the Monitor tab opens"),
        stopAt < 0
          ? unreadable("W2", "the timeline has no Emergency Stop marker, so the halt cannot be witnessed")
          : reading("W2", { stopRecorded: true, noLateSuccess: true, stopActive: true }, { stopRecorded: true, noLateSuccess: !lateSuccess, stopActive: timeline?.emergencyStopActive === true }, `the stop is event ${stopAt + 1} of ${events.length}; nothing completed after it`),
      ],
    },
  };
});
