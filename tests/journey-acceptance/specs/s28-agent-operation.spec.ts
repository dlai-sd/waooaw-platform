// Implements: validation/acceptance/plans/slice-6-agent-operation-dma-journey.v1.yaml steps S28 to S31
// Constitutional basis: C-001 (Emergency Stop), C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)
import { reading } from "../lib/claim.ts";
import { BlockedByFlag, NotCovered } from "../lib/step.ts";
import { acceptanceStep } from "./support/acceptance.ts";
import { startTrial } from "./support/ui.ts";

const MODES = ["INDUCT", "GOALS", "OPERATIONS"];

interface Frame {
  modesDeclared?: boolean;
  modes?: Array<{ modeId: string }>;
  home?: string;
}

acceptanceStep("S28", { covers: ["WC174-R001", "WC174-R002"] }, async ({ customer, run }) => {
  const { page } = await customer("A");
  const known = run.value("relationshipId");
  const relationship = known ?? (await startTrial(page, run.agent.offer)).relationshipId;
  run.setValue("relationshipId", relationship);
  const answer = await run.platform(page, `/api/relationships/${relationship}/operation/frame`);
  if (answer.status !== 200) {
    throw new BlockedByFlag(`the operation frame route answered HTTP ${answer.status}; this build is not deployed on Demo yet (owner: Founder deploys, author reads back)`);
  }
  const frame = answer.json as Frame | undefined;
  await page.goto(`/relationships/${relationship}`);
  const railModes = await page.locator("[data-mode]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-mode") ?? ""));
  const calendarOpen = await page.getByRole("heading", { name: /calendar/i }).count();
  const frameText = JSON.stringify(frame ?? {}).toLowerCase();
  return {
    reached: "L3",
    readings: {
      "S28-C1": [
        reading(
          "W1",
          { modes: MODES, calendarHome: true },
          { modes: railModes.filter((mode) => MODES.includes(mode)), calendarHome: calendarOpen > 0 },
          "the mode rail lists the three declared modes and the Calendar is the opening surface",
        ),
        reading(
          "W2",
          { modesDeclared: true, agentNamed: false },
          { modesDeclared: frame?.modesDeclared === true, agentNamed: frameText.includes(run.agent.id.toLowerCase()) },
          "the platform frame carries the agent's declared modes and names no agent",
        ),
      ],
    },
  };
});

acceptanceStep("S29", { covers: ["WC174-R008", "WC174-R009", "WC174-R010", "WC174-R013", "WC174-R014"] }, async () => {
  // Owner: Founder deploys; the author then runs this on Demo with one tester account (development-mode Meta app).
  throw new BlockedByFlag("this build is not deployed on Demo and no tester account is connected (owner: Founder deploys, author reads back)");
});

acceptanceStep("S30", { covers: ["WC174-R025"] }, async () => {
  // Owner: author, after S29 has published one post to the tester account.
  throw new BlockedByFlag("results and the digest need the S29 tester post (owner: author, after Demo deployment)");
});

acceptanceStep("S31", { covers: ["WC174-R015", "WC174-R025"] }, async () => {
  // Owner: Platform IT Expert. The second sealed image exists and runs in compose; its Terraform and CI wiring is not done.
  throw new NotCovered("the fixture agent image has no Terraform or deployment wiring yet (owner: Platform IT Expert, follow-up deployment wiring)");
});
