// Implements: validation/acceptance/plans/slice-3-hire-and-selection.v1.yaml steps S10, S11
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { reading, unreadable } from "../lib/claim.ts";
import { BlockedByFlag } from "../lib/step.ts";
import { acceptanceStep } from "./support/acceptance.ts";
import { environment } from "./support/context.ts";
import { parseSetCookie } from "../lib/cookies.ts";
import { acceptTerms, openProfessionalDisclosure, startTrial } from "./support/ui.ts";

const COOKIE = "waooaw_my_agents_selection";
const rupeesToPaise = (text: string): number | undefined => {
  const amount = /(?:₹|INR)\s?([\d,]+(?:\.\d+)?)/u.exec(text)?.[1];
  return amount === undefined ? undefined : Math.round(Number(amount.replace(/,/gu, "")) * 100);
};

acceptanceStep("S10", { covers: ["AE-01-S08", "WC107-R012"] }, async ({ customer, run }) => {
  const coupon = environment("ACCEPTANCE_DEMO_COUPON_CODE");
  if (coupon === undefined) {
    throw new BlockedByFlag("the acceptance test coupon is not readable from the environment's Key Vault");
  }
  const { page } = await customer("A");
  const orders: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/acquisition/hire-checkout")) {
      orders.push(request.url());
    }
  });
  await openProfessionalDisclosure(page, run.agent.offer);
  await page.getByRole("button", { name: /review hire/i }).click();
  await acceptTerms(page);
  const hireButton = page.getByRole("button", { name: /continue to razorpay|confirm hire/i });
  const before = rupeesToPaise((await hireButton.textContent()) ?? "");
  const preview = page.waitForResponse((response) => response.url().includes("/api/acquisition/hire-preview") && response.request().method() === "POST", { timeout: 60_000 });
  await page.locator("#disclosure-coupon-code").fill(coupon);
  await page.getByRole("button", { name: /^apply$/i }).click();
  const answer = await preview;
  const body = (await answer.json().catch(() => ({}))) as { coupon_code?: string; payable_inr_paise?: number };
  await page.getByText(/coupon applied/i).waitFor({ timeout: 30_000 });
  const after = rupeesToPaise((await hireButton.textContent()) ?? "");
  const cleanAddress = !decodeURIComponent(page.url()).toUpperCase().includes(coupon.toUpperCase());
  return {
    reached: "L3",
    readings: {
      "S10-C1": [
        reading(
          "W1",
          { changed: true, cleanAddress: true, ordersBeforeApply: 0 },
          { changed: before !== undefined && after !== undefined && after < before, cleanAddress, ordersBeforeApply: orders.length },
          `Hire command showed ${before ?? "no amount"} before and ${after ?? "no amount"} paise after Apply`,
        ),
        typeof body.payable_inr_paise !== "number"
          ? unreadable("W2", `the hire-preview route answered HTTP ${answer.status()} without a payable amount for the acceptance coupon`)
          : reading("W2", body.payable_inr_paise, after, "the amount on the Hire command equals the amount the platform validated"),
      ],
    },
  };
});

acceptanceStep("S11", { covers: ["AE-01-S05", "WC107-R016"] }, async ({ customer, run }) => {
  const { page, context } = await customer("B");
  const handoff = await startTrial(page, run.agent.offer);
  const cookie = parseSetCookie(handoff.setCookie, COOKIE);
  const cleanAddress = new URL(page.url()).search === "";
  const focused = await page
    .locator("[aria-describedby='my-agents-selection-confirmation']")
    .first()
    .waitFor({ state: "visible", timeout: 30_000 })
    .then(() => true)
    .catch(() => false);
  const confirmationShown = /trial started/i.test(await page.locator("#my-agents-selection-confirmation").innerText().catch(() => ""));
  let replayStatus: number | undefined;
  if (cookie !== undefined) {
    await context.addCookies([{ name: COOKIE, value: cookie.value, url: run.profile.origins.web, httpOnly: true, secure: true, sameSite: "Strict", path: "/professionals/mine" }]);
    replayStatus = (await page.request.get(`${run.profile.origins.web}/professionals/mine/selection`, { failOnStatusCode: false })).status();
  }
  const carriesNoIdentifier = cookie !== undefined && !cookie.value.toLowerCase().includes(handoff.relationshipId.slice(0, 8));
  return {
    reached: "L5",
    readings: {
      "S11-C1": [
        reading("W1", { cleanAddress: true, selectedCard: true, confirmation: true }, { cleanAddress, selectedCard: focused, confirmation: confirmationShown }, "My Agents shows the selected card and Trial started with a clean address"),
        cookie === undefined
          ? unreadable("W2", "the trial confirmation did not set the My Agents hand-off cookie")
          : reading(
              "W2",
              { httpOnly: true, secure: true, sameSite: "strict", path: "/professionals/mine", carriesNoIdentifier: true, replayStatus: 204 },
              { httpOnly: cookie.httpOnly, secure: cookie.secure, sameSite: cookie.sameSite, path: cookie.path, carriesNoIdentifier, replayStatus },
              "cookie attributes and one-use replay",
            ),
      ],
    },
  };
});
