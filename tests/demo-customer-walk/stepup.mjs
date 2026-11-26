import { chromium } from "@playwright/test";
const ORIGIN = "https://cp.demo.waooaw.com";
const browser = await chromium.launch();
const page = await (await browser.newContext()).newPage();
await page.goto(ORIGIN + "/login", { waitUntil: "domcontentloaded" });
const targets = ["/admin/operations", "/admin/agent-operation", "/admin/azure-key-vault", "/founder", "/founder/access", "/access", "/admin/providers", "/admin/pricing", "/admin/pricing/rates", "/admin/pricing/packages", "/admin/pricing/packages/new", "/home"];
for (const target of targets) {
  const r = await page.evaluate(async (t) => {
    const csrfToken = (await (await fetch("/api/auth/csrf")).json()).csrfToken;
    const x = await fetch("/api/auth/signin/keycloak-google", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ csrfToken, callbackUrl: t, waooawIntent: "LOGIN", json: "true" }) });
    const b = await x.json().catch(() => null);
    return { status: x.status, code: b?.code, started: typeof b?.url === "string" };
  }, target);
  console.log("STEPUP", target.padEnd(30), JSON.stringify(r));
}
await browser.close();
