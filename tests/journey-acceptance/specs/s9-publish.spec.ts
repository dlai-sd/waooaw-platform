// Implements: validation/acceptance/plans/slice-2-publish.v1.yaml steps S9, S9b
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import type { Page } from "@playwright/test";
import { reading, unreadable } from "../lib/claim.ts";
import { scanText } from "../lib/guards.ts";
import { deletePost, listPagePostIds, readPost } from "../lib/meta.ts";
import { pick } from "../lib/platform.ts";
import { acceptanceStep } from "./support/acceptance.ts";
import { connectFacebook, metaPage, metaSandbox } from "./support/meta.ts";
import { bodyText } from "./support/ui.ts";

const MAXIMUM_POST_LENGTH = 2000;

async function ensureConnected(page: Page): Promise<void> {
  await page.goto("/connections");
  await page.getByText(/connected|connect facebook/i).first().waitFor({ timeout: 30_000 });
}

acceptanceStep("S9", { covers: ["AE-02-S05", "PG-16", "WC149-R009"] }, async ({ customer, run }) => {
  const sandbox = metaSandbox();
  const { pageId, token } = metaPage();
  const { page, context } = await customer("A");
  await ensureConnected(page);
  if (!(await page.getByRole("button", { name: /^revoke/i }).first().isVisible().catch(() => false))) {
    await connectFacebook(run, page, context, sandbox);
  }
  const text = `WAOOAW acceptance ${run.state.runId} ${new Date().toISOString()}`;
  const before = await listPagePostIds(run.fetchImpl, token, pageId);
  await page.getByLabel(/post message/i).fill(text);
  await page.getByLabel(/i approve this exact post/i).check();
  await page.getByRole("button", { name: /publish post/i }).click();
  await page.getByText(/facebook post id/i).waitFor({ timeout: 60_000 });
  const screen = await bodyText(page);
  const postId = /facebook post id\s+([0-9_]+)/i.exec(screen)?.[1];
  const listed = await run.platform(page, "/api/provider-connections");
  const first = Array.isArray(listed.json) ? (listed.json[0] as Record<string, unknown> | undefined) : undefined;
  const status = first === undefined ? undefined : String(pick(first, ["status"]));
  const noToken = scanText(JSON.stringify(listed.json ?? {})).length === 0;
  let post: Awaited<ReturnType<typeof readPost>>;
  let after: string[] = [];
  try {
    post = postId === undefined ? undefined : await readPost(run.fetchImpl, token, postId);
    after = await listPagePostIds(run.fetchImpl, token, pageId);
  } finally {
    // The test Page stays clean whatever the verdict: the run deletes the one post it published.
    if (postId !== undefined && !(await deletePost(run.fetchImpl, token, postId))) {
      run.setValue("leftoverPost", postId);
    }
  }
  const added = after.filter((id) => !before.includes(id));
  return {
    reached: "L4",
    readings: {
      "S9-C1": [
        reading("W1", true, postId !== undefined, postId === undefined ? "no Facebook post id was shown" : "the screen shows the Facebook post id"),
        status === undefined
          ? unreadable("W2", "the provider-connections route returned no connection")
          : reading("W2", { status: "CONNECTED", noToken: true }, { status, noToken }, "the connection stays CONNECTED and no response carries a token"),
        postId === undefined
          ? unreadable("W3", "there is no post id to read from Graph")
          : reading("W3", { message: text, newPosts: 1 }, { message: post?.message, newPosts: added.length }, "Graph shows exactly the approved text, once"),
      ],
    },
  };
});

acceptanceStep("S9b", { covers: ["PG-16", "WC149-R009"] }, async ({ customer, run }) => {
  metaSandbox();
  const { pageId, token } = metaPage();
  const { page } = await customer("A");
  await ensureConnected(page);
  const before = await listPagePostIds(run.fetchImpl, token, pageId);
  const connections = await run.platform(page, "/api/provider-connections");
  const connectionId = Array.isArray(connections.json) ? String(pick(connections.json[0], ["id"])) : undefined;
  if (connectionId === undefined) {
    return { reached: "L2", readings: { "S9b-C1": [unreadable("W1", "no connected account to publish to"), unreadable("W2", "no connection"), unreadable("W3", "no connection")] } };
  }
  const refused: number[] = [];
  for (const message of ["", "x".repeat(MAXIMUM_POST_LENGTH + 1)]) {
    const response = await page.request.post(`${run.profile.origins.web}/api/provider-connections/${connectionId}/publish`, {
      data: { message, approved: true, approvalNote: "Approved by the acceptance run." },
      failOnStatusCode: false,
    });
    refused.push(response.status());
  }
  await page.goto("/connections");
  const publish = page.getByRole("button", { name: /publish post/i });
  await page.getByLabel(/post message/i).fill("");
  await page.getByLabel(/i approve this exact post/i).check();
  const uiBlocksEmpty = await publish.isDisabled();
  const after = await listPagePostIds(run.fetchImpl, token, pageId);
  return {
    reached: "L5",
    readings: {
      "S9b-C1": [
        reading("W1", true, uiBlocksEmpty, "the Publish post control stays disabled for an empty post"),
        reading("W2", true, refused.every((status) => status >= 400 && status < 500), `the platform answered ${refused.join(" and ")} to the empty and over-limit posts`),
        reading("W3", before, after, "the Page feed is unchanged after both attempts"),
      ],
    },
  };
});
