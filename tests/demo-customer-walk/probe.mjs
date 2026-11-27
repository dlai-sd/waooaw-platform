// Signs in as a throwaway customer and calls the listed same-origin API paths (PROBE_PATHS, comma separated), printing status,
// time and a short body for each. Read-only GETs; the throwaway customer is deleted afterwards. Run by scripts/run_demo_customer_walk.sh probe.
import { chromium } from "@playwright/test";
import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";

const ORIGIN = "https://cp.demo.waooaw.com";
const run = JSON.parse(readFileSync("/users/run.json", "utf8"));
const user = run.customers[process.env.WALK_USER || "B"];
const paths = (process.env.PROBE_PATHS || "/api/alert-controls/categories,/api/alert-controls/alerts").split(",");

function b32(text) { const a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; let bits = ""; for (const c of text.replace(/=+$/, "")) bits += a.indexOf(c).toString(2).padStart(5, "0"); const out = []; for (let i = 0; i + 8 <= bits.length; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2)); return Buffer.from(out); }
function totp(secret, now = Date.now()) { const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(now / 30000))); const h = createHmac("sha1", b32(secret)).update(counter).digest(); const o = h[h.length - 1] & 15; return String((((h[o] & 127) << 24) | (h[o + 1] << 16) | (h[o + 2] << 8) | h[o + 3]) % 1000000).padStart(6, "0"); }

const browser = await chromium.launch();
const page = await (await browser.newContext()).newPage();
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
for (const path of paths) {
  const result = await page.evaluate(async (p) => {
    const t0 = performance.now();
    const r = await fetch(p, { credentials: "same-origin" });
    return { status: r.status, ms: Math.round(performance.now() - t0), body: (await r.text()).replace(/eyJ[A-Za-z0-9_.-]{20,}/g, "<jwt>").slice(0, 300) };
  }, path);
  console.log("PROBE", path, JSON.stringify(result));
}
await browser.close();
