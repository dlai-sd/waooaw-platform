// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §6 Slice 1 Journey (customer actions)
// Constitutional basis: C-059 (Implementation Traceability)
import type { Page } from "@playwright/test";
import type { SyntheticCustomer } from "../../lib/keycloak.ts";
import { relationshipIdFromUrl } from "../../lib/platform.ts";
import { totp } from "../../lib/totp.ts";

/** Signs in through the product's own entry and the real Keycloak form, including the OTP step-up when it is asked for. */
export async function signIn(page: Page, customer: SyntheticCustomer): Promise<void> {
  await page.goto("/login");
  const credentialEntry = page.getByRole("button", { name: /email|keycloak|continue with email/i }).first();
  if (await credentialEntry.isEnabled({ timeout: 5000 }).catch(() => false)) {
    await credentialEntry.click();
  } else {
    // The login page offers brokered providers; local synthetic users start from the same NextAuth Keycloak provider.
    await page.goto("/api/auth/signin");
    await page.getByRole("button", { name: /keycloak/i }).click();
  }
  await page.locator("#username").fill(customer.username);
  await page.locator("#password").fill(customer.password);
  await page.locator("#kc-login").click();
  const asksForOtp = await page
    .locator("#otp")
    .waitFor({ state: "visible", timeout: 8000 })
    .then(() => true)
    .catch(() => false);
  if (asksForOtp) {
    await page.locator("#otp").fill(totp(customer.otpSecret, Date.now()));
    await page.locator("#kc-login").click();
  }
  await page.waitForURL((url) => !url.pathname.startsWith("/login") && !url.pathname.startsWith("/api/auth"), { timeout: 60_000 });
}

export async function signOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: /sign out|log out/i }).first().click();
  await page.waitForURL((url) => url.pathname === "/" || url.pathname.startsWith("/login"), { timeout: 30_000 });
}

export async function bodyText(page: Page): Promise<string> {
  return page.locator("body").innerText();
}

/** What page script can reach: storage and cookies visible to JavaScript. A token here fails the claim. */
export async function scriptVisibleState(page: Page): Promise<string> {
  return page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage }, cookie: document.cookie }));
}

export async function openProfessionalDisclosure(page: Page, name: RegExp): Promise<void> {
  await page.goto("/marketplace");
  const card = page.locator("article, li, section").filter({ has: page.getByRole("heading", { name }) }).first();
  await card.getByRole("link", { name: /open expanded disclosure/i }).click();
  await page.waitForLoadState("networkidle");
}

export async function acceptTerms(page: Page): Promise<void> {
  const checkbox = page.getByRole("checkbox").first();
  await checkbox.check();
}

/** The customer path to a free trial: disclosure, review, accept the terms, confirm. Returns the new relationship's id. */
export async function startTrial(page: Page, offer: RegExp): Promise<string> {
  await openProfessionalDisclosure(page, offer);
  await page.getByRole("button", { name: /review free .*trial/i }).click();
  await acceptTerms(page);
  await page.getByRole("button", { name: /confirm free .*trial/i }).click();
  await page.waitForURL((url) => relationshipIdFromUrl(url.toString()) !== undefined, { timeout: 90_000 });
  const relationshipId = relationshipIdFromUrl(page.url());
  if (relationshipId === undefined) {
    throw new Error("the trial did not lead to a relationship page");
  }
  return relationshipId;
}

/** Collects Razorpay order and checkout identifiers from the application's own JSON responses (never from the provider page). */
export function captureCheckoutIdentifiers(page: Page): { orderId?: string; relationshipId?: string; intentId?: string } {
  const captured: { orderId?: string; relationshipId?: string; intentId?: string } = {};
  page.on("response", async (response) => {
    if (!response.url().includes("/api/") || !(response.headers()["content-type"] ?? "").includes("json")) {
      return;
    }
    try {
      const body: unknown = await response.json();
      const text = JSON.stringify(body);
      captured.orderId ??= /"(?:razorpayOrderId|orderId)":"(order_[A-Za-z0-9_-]+)"/u.exec(text)?.[1];
      captured.intentId ??= /"checkoutIntentId":"([0-9a-f-]{36})"/iu.exec(text)?.[1];
      captured.relationshipId ??= /"relationshipId":"([0-9a-f-]{36})"/iu.exec(text)?.[1];
    } catch {
      // Not every JSON response is readable after navigation.
    }
  });
  return captured;
}

/** Pays in Razorpay's sandbox Checkout with the documented test card; `failure` takes the bank page's failure path. */
export async function payInSandboxCheckout(page: Page, outcome: "success" | "failure"): Promise<void> {
  const checkout = page.frameLocator("iframe.razorpay-checkout-frame");
  await checkout.getByText(/^card$/i).first().click({ timeout: 60_000 });
  await checkout.getByPlaceholder(/card number/i).fill("5267 3181 8797 5449");
  await checkout.getByPlaceholder(/mm ?\/ ?yy/i).fill("12/30");
  await checkout.getByPlaceholder(/cvv/i).fill("123");
  const popup = page.waitForEvent("popup", { timeout: 60_000 });
  await checkout.getByRole("button", { name: /pay/i }).first().click();
  const bank = await popup;
  await bank.getByRole("button", { name: outcome === "success" ? /success/i : /failure/i }).click();
}
