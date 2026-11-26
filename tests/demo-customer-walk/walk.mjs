import { chromium } from "@playwright/test";
import { createHmac } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";

const ORIGIN = "https://cp.demo.waooaw.com";
const OUT = "/out";
const run = JSON.parse(readFileSync("/users/run.json", "utf8"));
const user = run.customers[process.env.WALK_USER ?? "A"];

function b32(text) { const a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; let bits = ""; for (const c of text.replace(/=+$/, "")) bits += a.indexOf(c).toString(2).padStart(5, "0"); const out = []; for (let i = 0; i + 8 <= bits.length; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2)); return Buffer.from(out); }
function totp(secret, now = Date.now()) { const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(now / 30000))); const h = createHmac("sha1", b32(secret)).update(counter).digest(); const o = h[h.length - 1] & 15; const code = ((h[o] & 127) << 24 | h[o + 1] << 16 | h[o + 2] << 8 | h[o + 3]) % 1000000; return String(code).padStart(6, "0"); }

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
const page = await context.newPage();
const findings = [];
let current = "login";
const events = { console: [], failed: [] };
page.on("console", (m) => { if (m.type() === "error") events.console.push({ page: current, text: m.text().slice(0, 200) }); });
page.on("response", (r) => { const u = r.url(); if (r.status() >= 400 && (u.includes("/api/") || u.startsWith(ORIGIN))) events.failed.push({ page: current, status: r.status(), url: u.replace(ORIGIN, "").slice(0, 120) }); });

// sign in through the product's own entry and the real Keycloak form
await page.goto(ORIGIN + "/login", { waitUntil: "domcontentloaded" });
await page.screenshot({ path: `${OUT}/00-login.png`, fullPage: true });
const loginInfo = await page.evaluate(() => ({ buttons: [...document.querySelectorAll("button,a")].map((b) => b.textContent.trim().slice(0, 40) + (b.disabled ? " [disabled]" : "")).filter(Boolean).slice(0, 20), text: document.body.innerText.replace(/\s+/g, " ").slice(0, 400) }));
findings.push({ page: "/login", ...loginInfo });
// The login page offers only Google and Facebook (Email is disabled), so start the plain Keycloak provider the way
// NextAuth's own form does: a CSRF token, then a POST to /api/auth/signin/keycloak.
const started = await page.evaluate(async () => {
  const csrfToken = (await (await fetch("/api/auth/csrf")).json()).csrfToken;
  const response = await fetch("/api/auth/signin/keycloak", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ csrfToken, callbackUrl: "/home", waooawIntent: "LOGIN", json: "true" }),
  });
  return { status: response.status, body: await response.json().catch(() => null) };
});
findings.push({ page: "signin-start-response", status: started.status, code: started.body?.code, hasUrl: typeof started.body?.url === "string" });
if (typeof started.body?.url === "string") await page.goto(started.body.url);
const reached = await page.waitForSelector("#username", { timeout: 20000 }).then(() => true).catch(() => false);
if (!reached) {
  findings.push({ page: "signin-start", url: page.url(), text: await page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").slice(0, 400)) });
  await page.screenshot({ path: `${OUT}/00-signin-failed.png`, fullPage: true });
  writeFileSync(`${OUT}/walk.json`, JSON.stringify({ findings, events }, null, 1));
  await browser.close();
  console.log("SIGN-IN DID NOT REACH THE KEYCLOAK FORM", page.url());
  process.exit(3);
}
await page.locator("#username").fill(user.username);
await page.locator("#password").fill(user.password);
await page.locator("#kc-login").click();
const otp = await page.locator("#otp").waitFor({ state: "visible", timeout: 8000 }).then(() => true).catch(() => false);
if (otp) { await page.locator("#otp").fill(totp(user.otpSecret)); await page.locator("#kc-login").click(); }
await page.waitForURL((u) => !u.pathname.startsWith("/login") && !u.pathname.startsWith("/api/auth") && !u.host.startsWith("auth."), { timeout: 60000 }).catch((e) => findings.push({ page: "login", note: "sign-in did not return to the product: " + page.url() }));
await page.screenshot({ path: `${OUT}/00-after-signin.png` });
findings.push({ page: "login", landedOn: page.url().replace(ORIGIN, "") });

for (const path of ["/api/identity/session", "/api/identity/account", "/api/identity/profile", "/api/identity/settings"]) {
  const r = await page.evaluate(async (u) => { const x = await fetch(u); const t = await x.text(); return { status: x.status, body: t.slice(0, 260) }; }, path);
  findings.push({ page: path, status: r.status, text: r.body.replace(/eyJ[A-Za-z0-9_.-]{20,}/g, "<jwt>") });
}
const authKeys = await page.evaluate(async () => { const x = await (await fetch("/api/auth/session")).json(); return { keys: Object.keys(x), authenticated: x.authenticated, founder: x.founder, error: x.error }; });
findings.push({ page: "/api/auth/session", ...authKeys });
const routes = ["/home", "/marketplace", "/professionals/mine", "/profile", "/settings", "/alerts", "/connections", "/billing", "/employment-contract", "/admin/operations", "/founder", "/admin/pricing"];
let n = 1;
for (const route of routes) {
  current = route;
  const t0 = Date.now();
  const response = await page.goto(ORIGIN + route, { waitUntil: "domcontentloaded", timeout: 45000 }).catch((e) => null);
  await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
  const info = await page.evaluate(() => ({
    title: document.title,
    h1: [...document.querySelectorAll("h1,h2")].slice(0, 4).map((h) => h.textContent.trim().slice(0, 60)),
    tabs: [...document.querySelectorAll('[role="tab"]')].map((t) => t.textContent.trim().slice(0, 30)),
    buttons: [...document.querySelectorAll("button")].filter((b) => b.offsetParent !== null).map((b) => b.textContent.trim().slice(0, 30)).filter(Boolean).slice(0, 14),
    links: [...document.querySelectorAll("nav a, aside a")].map((a) => a.textContent.trim().slice(0, 24) + "→" + a.getAttribute("href")).slice(0, 14),
    text: document.body.innerText.replace(/\s+/g, " ").slice(0, 260),
    overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
  })).catch(() => ({}));
  await page.screenshot({ path: `${OUT}/${String(n).padStart(2, "0")}-${route.replace(/\W+/g, "_") || "root"}.png`, fullPage: true }).catch(() => {});
  findings.push({ page: route, status: response?.status() ?? null, finalUrl: page.url().replace(ORIGIN, ""), ms: Date.now() - t0, ...info });
  n++;
}
// click every tab on the pages that have them
for (const route of ["/profile", "/settings"]) {
  current = route + "#tabs";
  await page.goto(ORIGIN + route, { waitUntil: "domcontentloaded" }).catch(() => {});
  await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => {});
  const tabs = await page.locator('[role="tab"]').all();
  for (const tab of tabs) { const label = (await tab.textContent())?.trim(); await tab.click({ timeout: 4000 }).catch(() => findings.push({ page: route, tab: label, note: "tab not clickable" })); await page.waitForTimeout(600); findings.push({ page: route, tab: label, text: (await page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").slice(0, 160))) }); }
}
writeFileSync(`${OUT}/walk.json`, JSON.stringify({ findings, events }, null, 1));
await browser.close();
console.log("WALK DONE", findings.length, "findings;", events.failed.length, "failed responses;", events.console.length, "console errors");
