// Implements: validation/acceptance/plans/slice-1-discover-to-connect.v1.yaml steps S5, S5b
// Constitutional basis: C-059 (Implementation Traceability), C-023 (Evidence First)
import { reading, unreadable } from "../lib/claim.ts";
import { pick } from "../lib/platform.ts";
import { assertRazorpayTestMode, capturedTotal, readOrderPayments, signWebhook } from "../lib/razorpay.ts";
import { BlockedByFlag } from "../lib/step.ts";
import { acceptanceStep, requirePassed } from "./support/acceptance.ts";
import { environment } from "./support/context.ts";
import { acceptTerms, bodyText, captureCheckoutIdentifiers, openProfessionalDisclosure, payInSandboxCheckout } from "./support/ui.ts";

const OFFER = /digital marketing/i;

function razorpayCredentials(prefix: string): { keyId: string; keySecret: string } {
  const keyId = environment("ACCEPTANCE_RAZORPAY_KEY_ID");
  const keySecret = environment("ACCEPTANCE_RAZORPAY_KEY_SECRET");
  if (keyId === undefined || keySecret === undefined) {
    throw new BlockedByFlag("Razorpay test credentials are not readable from the environment's Key Vault");
  }
  assertRazorpayTestMode(keyId, prefix);
  return { keyId, keySecret };
}

acceptanceStep("S5", { covers: ["AE-01-S08", "PG-11", "PG-12", "WC107-R013", "WC107-R014"] }, async ({ customer, run }) => {
  requirePassed(run, "S4");
  const credentials = razorpayCredentials(run.profile.sandbox.razorpay_key_id_prefix);
  const relationshipId = run.value("relationshipId");
  if (relationshipId === undefined) {
    throw new Error("no relationship from the earlier steps");
  }
  const { page } = await customer("A");
  const ids = captureCheckoutIdentifiers(page);
  await page.goto(`/relationships/${relationshipId}`);
  const shownAmount = /(?:₹|INR)\s?([\d,]+(?:\.\d+)?)/u.exec(await bodyText(page))?.[1];
  await page.getByRole("button", { name: /confirm contract funding/i }).click();
  await payInSandboxCheckout(page, "success");
  await page.getByRole("button", { name: /complete paid activation/i }).click({ timeout: 90_000 });
  await page.waitForLoadState("networkidle");
  const screen = await bodyText(page);
  const active = /\bactive\b/i.test(screen);
  const state = pick((await run.platform(page, `/api/relationships/${relationshipId}/workbench/`)).json, ["lifecycleState", "state", "status"]);
  const orderId = ids.orderId;
  if (orderId !== undefined) {
    run.setValue("orderId", orderId);
  }
  const payments = orderId === undefined ? undefined : capturedTotal(await readOrderPayments(run.fetchImpl, credentials, orderId));
  const amountPaise = shownAmount === undefined ? undefined : Math.round(Number(shownAmount.replace(/,/gu, "")) * 100);
  return {
    reached: "L4",
    readings: {
      "S5-C1": [
        reading("W1", true, active, "the relationship shows Active after payment"),
        state === undefined
          ? unreadable("W2", "the workbench route did not expose the lifecycle state")
          : reading("W2", true, /active/i.test(String(state)), `platform state ${String(state)}`),
        payments === undefined || amountPaise === undefined
          ? unreadable("W3", "the shown amount or the Razorpay order identifier was not visible in the application's responses")
          : reading("W3", { count: 1, amountPaise }, payments, "sandbox payments captured for the order"),
      ],
    },
  };
});

acceptanceStep("S5b", { covers: ["PG-12", "WC107-R014"] }, async ({ customer, run }) => {
  requirePassed(run, "S5");
  const credentials = razorpayCredentials(run.profile.sandbox.razorpay_key_id_prefix);
  const webhookSecret = environment("ACCEPTANCE_RAZORPAY_WEBHOOK_SECRET");
  const orderId = run.value("orderId");
  const relationshipId = run.value("relationshipId");
  if (webhookSecret === undefined || orderId === undefined || relationshipId === undefined) {
    throw new BlockedByFlag("the webhook secret or the paid order from step S5 is not available");
  }
  const { page } = await customer("A");
  const before = capturedTotal(await readOrderPayments(run.fetchImpl, credentials, orderId));
  const evidenceBefore = JSON.stringify((await run.platform(page, `/api/relationships/${relationshipId}/workbench/evidence`)).json ?? null);
  const payments = await readOrderPayments(run.fetchImpl, credentials, orderId);
  const paymentId = payments.find((payment) => payment.captured)?.paymentId;
  const body = JSON.stringify({
    event: "payment.captured",
    payload: { payment: { entity: { id: paymentId, order_id: orderId, status: "captured" } } },
  });
  const replay = await run.fetchImpl(`${run.profile.origins.api}/api/v1/payments/webhooks/razorpay`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Razorpay-Signature": signWebhook(body, webhookSecret) },
    body,
  });
  const after = capturedTotal(await readOrderPayments(run.fetchImpl, credentials, orderId));
  const evidenceAfter = JSON.stringify((await run.platform(page, `/api/relationships/${relationshipId}/workbench/evidence`)).json ?? null);
  await openProfessionalDisclosure(page, OFFER);
  await page.getByRole("button", { name: /review hire/i }).click();
  await acceptTerms(page);
  const ids = captureCheckoutIdentifiers(page);
  await page.getByRole("button", { name: /continue to razorpay/i }).click();
  await payInSandboxCheckout(page, "failure");
  await page.waitForLoadState("networkidle");
  const declinedActive = /\bactive\b/i.test(await bodyText(page)) && /payment (captured|successful)/i.test(await bodyText(page));
  const declinedState =
    ids.relationshipId === undefined ? undefined : pick((await run.platform(page, `/api/relationships/${ids.relationshipId}/workbench/`)).json, ["lifecycleState", "state", "status"]);
  return {
    reached: "L5",
    readings: {
      "S5b-C1": [
        reading("W1", { replayAccepted: true, declinedLooksActive: false }, { replayAccepted: replay.status < 500, declinedLooksActive: declinedActive }, "replay answered and the declined payment is not shown as paid"),
        declinedState === undefined
          ? unreadable("W2", "the declined hire's relationship state was not readable through a customer route")
          : reading("W2", { unchanged: true, declinedActive: false }, { unchanged: evidenceBefore === evidenceAfter, declinedActive: /active/i.test(String(declinedState)) }, "evidence unchanged by the replay; declined hire not Active"),
        reading("W3", before, after, "captured payments for the order before and after the replay"),
      ],
    },
  };
});
