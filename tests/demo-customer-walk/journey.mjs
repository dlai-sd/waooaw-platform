// Customer journey on Demo as a throwaway customer: Register entry, sign-in, Trial, Hire, and the customer tabs afterwards.
// Records every API call (method, status, short body) and a screenshot per step. Report-only apart from the Trial/Hire the
// customer itself starts; the throwaway customer is deleted afterwards. Run by scripts/run_demo_customer_walk.sh journey.
import { chromium } from "@playwright/test";
import { createHmac } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";

const ORIGIN = "https://cp.demo.waooaw.com";
const OUT = "/out";
const run = JSON.parse(readFileSync("/users/run.json", "utf8"));
const user = run.customers[process.env.WALK_USER || "B"];
const MODE = process.env.JOURNEY || "explore";

function b32(text) { const a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; let bits = ""; for (const c of text.replace(/=+$/, "")) bits += a.indexOf(c).toString(2).padStart(5, "0"); const out = []; for (let i = 0; i + 8 <= bits.length; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2)); return Buffer.from(out); }
function totp(secret, now = Date.now()) { const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(now / 30000))); const h = createHmac("sha1", b32(secret)).update(counter).digest(); const o = h[h.length - 1] & 15; const code = ((h[o] & 127) << 24 | h[o + 1] << 16 | h[o + 2] << 8 | h[o + 3]) % 1000000; return String(code).padStart(6, "0"); }

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
const page = await context.newPage();
const log = [];
const calls = [];
let step = "start";
page.on("response", async (r) => {
  const u = new URL(r.url());
  if (u.origin !== ORIGIN || !/^\/(api|_next\/data)/.test(u.pathname) || u.pathname.startsWith("/api/auth/csrf")) return;
  const body = r.status() >= 300 ? (await r.text().catch(() => "")).replace(/eyJ[A-Za-z0-9_.-]{20,}/g, "<jwt>").slice(0, 240) : "";
  calls.push({ step, method: r.request().method(), status: r.status(), path: u.pathname + u.search.slice(0, 60), body });
});
const view = () => page.evaluate(() => ({
  url: location.pathname,
  h: [...document.querySelectorAll("h1,h2,h3")].slice(0, 6).map((h) => h.textContent.trim().slice(0, 70)),
  dialog: [...document.querySelectorAll('[role="dialog"],[role="alertdialog"]')].map((d) => d.innerText.replace(/\s+/g, " ").slice(0, 500)),
  alerts: [...document.querySelectorAll('[role="alert"],[role="status"]')].map((d) => d.innerText.replace(/\s+/g, " ").slice(0, 200)),
  buttons: [...document.querySelectorAll("button,a[role=button]")].filter((b) => b.offsetParent !== null).map((b) => b.textContent.trim().slice(0, 40) + (b.disabled ? " [disabled]" : "")).filter(Boolean).slice(0, 16),
  text: document.body.innerText.replace(/\s+/g, " ").slice(0, 700),
}));
let n = 0;
async function snap(name, note = {}) {
  step = name;
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  const v = await view().catch(() => ({}));
  await page.screenshot({ path: `${OUT}/j${String(++n).padStart(2, "0")}-${name}.png`, fullPage: true }).catch(() => {});
  log.push({ step: name, ...note, ...v });
}

// 1. Register entry, before any sign-in
await page.goto(ORIGIN + "/login", { waitUntil: "domcontentloaded" });
await snap("login-page");
const register = page.getByRole("button", { name: /^register$/i }).or(page.getByRole("link", { name: /^register$/i }));
if (await register.count()) {
  await register.first().click().catch(() => {});
  await page.waitForTimeout(1500);
  await snap("register-clicked", { landed: page.url().replace(ORIGIN, "") });
} else log.push({ step: "register", note: "no Register control found" });

// 2. Sign in through the real Keycloak form
await page.goto(ORIGIN + "/login", { waitUntil: "domcontentloaded" });
const started = await page.evaluate(async () => {
  const csrfToken = (await (await fetch("/api/auth/csrf")).json()).csrfToken;
  const r = await fetch("/api/auth/signin/keycloak", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ csrfToken, callbackUrl: "/home", waooawIntent: "LOGIN", json: "true" }) });
  return (await r.json().catch(() => ({}))).url;
});
await page.goto(started);
await page.locator("#username").fill(user.username);
await page.locator("#password").fill(user.password);
await page.locator("#kc-login").click();
if (await page.locator("#otp").waitFor({ state: "visible", timeout: 8000 }).then(() => true).catch(() => false)) {
  await page.locator("#otp").fill(totp(user.otpSecret));
  await page.locator("#kc-login").click();
}
await page.waitForURL((u) => u.origin === ORIGIN && !u.pathname.startsWith("/login") && !u.pathname.startsWith("/api/auth"), { timeout: 60000 }).catch(() => {});
await snap("signed-in");

// 3. Marketplace, then open Trial and Hire reviews
await page.goto(ORIGIN + "/marketplace", { waitUntil: "domcontentloaded" });
await snap("marketplace");
const hireControl = await page.getByRole("button", { name: /review hire/i }).first();
log.push({ step: "hire-control", disabled: await hireControl.isDisabled().catch(() => null), priceText: await page.evaluate(() => (document.body.innerText.match(/Price cannot be shown[^.]*\.?|₹[\d,.]+[^\n]{0,40}/) ?? [""])[0]) });
if (MODE === "explore" || MODE === "trial") {
  await page.getByRole("button", { name: /review free 14-day trial/i }).first().click().catch((e) => log.push({ step: "trial-click", error: String(e).slice(0, 160) }));
  await page.waitForTimeout(1500);
  await snap("trial-review");
  const contract = page.getByRole("link", { name: /employment contract/i }).first();
  const href = await contract.getAttribute("href").catch(() => null);
  const probe = href ? await page.evaluate(async (h) => { const r = await fetch(h); return { status: r.status, finalUrl: r.url.replace(location.origin, "") }; }, href) : null;
  log.push({ step: "contract-link", href, probe });
}
if (MODE === "register") {
  await page.goto(ORIGIN + "/register?returnTo=%2Fmarketplace", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3000);
  await snap("register-signed-in");
  const email = page.locator('input[name="email"]');
  const name = page.locator('input[autocomplete="name"]');
  if (await name.count()) {
    await name.fill("Synthetic Customer");
    await page.locator('input[autocomplete="organization"]').fill("Synthetic Test Clinic");
    await page.locator("form input").last().fill("Dental clinic");
    await page.getByRole("button", { name: /save and continue/i }).click();
    await page.waitForTimeout(6000);
    await snap("register-profile-saved");
    const phone = page.locator('input[type="tel"]');
    if (await phone.count()) {
      await phone.fill("+15555550134");
      await page.getByRole("button", { name: /send whatsapp verification code/i }).click().catch((e) => log.push({ step: "mobile-start-click", error: String(e).slice(0, 160) }));
      await page.waitForTimeout(8000);
      await snap("register-mobile-start");
    }
  }
  if (await email.count()) {
    await email.fill(user.email);
    await page.getByRole("button", { name: /send|verify|continue|code/i }).first().click().catch((e) => log.push({ step: "email-start-click", error: String(e).slice(0, 160) }));
    await page.waitForTimeout(5000);
    await snap("register-email-start");
  } else log.push({ step: "register", note: "no email field shown to the signed-in customer" });
}
if (MODE === "trial") {
  await page.getByRole("checkbox").first().check().catch((e) => log.push({ step: "accept-check", error: String(e).slice(0, 160) }));
  const confirm = page.getByRole("button", { name: /confirm free 14-day trial/i });
  log.push({ step: "confirm-state", disabledAfterAccept: await confirm.isDisabled().catch(() => null) });
  await snap("trial-accepted");
  await confirm.click({ timeout: 5000 }).catch((e) => log.push({ step: "confirm-click", error: String(e).slice(0, 160) }));
  await page.waitForTimeout(6000);
  await snap("trial-confirmed");
  for (const route of ["/professionals/mine", "/alerts", "/profile", "/settings", "/connections", "/billing", "/marketplace"]) {
    await page.goto(ORIGIN + route, { waitUntil: "domcontentloaded" });
    await snap("after-trial" + route.replace(/\W+/g, "-"));
  }
}
writeFileSync(`${OUT}/journey-${MODE}.json`, JSON.stringify({ log, calls }, null, 1));
await browser.close();
console.log("JOURNEY", MODE, "steps", log.length, "calls", calls.length);
