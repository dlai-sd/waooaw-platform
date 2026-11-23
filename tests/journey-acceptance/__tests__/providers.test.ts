// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 W2 and W3 readers
// Constitutional basis: C-059 (Implementation Traceability)
import assert from "node:assert/strict";
import { test } from "node:test";
import { MetaModeError, assertTestUser, readGrantedPermissions } from "../lib/meta.ts";
import { collectIdentifiers, pick, relationshipIdFromUrl } from "../lib/platform.ts";
import { ProviderModeError, assertRazorpayTestMode, capturedTotal, readOrderPayments, signWebhook } from "../lib/razorpay.ts";
import type { FetchLike } from "../lib/razorpay.ts";

function answer(status: number, body: unknown): ReturnType<FetchLike> {
  return Promise.resolve({ ok: status < 300, status, text: async () => JSON.stringify(body) });
}

test("a live Razorpay key stops the run before any call", async () => {
  assert.throws(() => assertRazorpayTestMode("rzp_live_abcdef"), ProviderModeError);
  assert.doesNotThrow(() => assertRazorpayTestMode("rzp_test_abcdef"));
  let called = false;
  const spy: FetchLike = () => {
    called = true;
    return answer(200, {});
  };
  await assert.rejects(readOrderPayments(spy, { keyId: "rzp_live_x", keySecret: "s" }, "order_abc"), ProviderModeError);
  assert.equal(called, false);
});

test("the sandbox order payments are read with basic auth and summarised", async () => {
  let seen: { url: string; authorization?: string } | undefined;
  const fetchImpl: FetchLike = (url, init) => {
    seen = { url, authorization: init?.headers?.Authorization };
    return answer(200, {
      items: [
        { id: "pay_1", status: "captured", amount: 236000 },
        { id: "pay_2", status: "failed", amount: 236000 },
        { id: "pay_3", status: "authorized", amount: 100, captured: true },
      ],
    });
  };
  const payments = await readOrderPayments(fetchImpl, { keyId: "rzp_test_abc", keySecret: "secret" }, "order_abc");
  assert.equal(seen?.url, "https://api.razorpay.com/v1/orders/order_abc/payments");
  assert.equal(seen?.authorization, `Basic ${Buffer.from("rzp_test_abc:secret").toString("base64")}`);
  assert.deepEqual(capturedTotal(payments), { count: 2, amountPaise: 236100 });
  assert.deepEqual(capturedTotal([]), { count: 0, amountPaise: 0 });
  const empty = await readOrderPayments(() => answer(200, {}), { keyId: "rzp_test_abc", keySecret: "s" }, "order_abc");
  assert.deepEqual(empty, []);
});

test("a malformed order id or a provider error is refused", async () => {
  const credentials = { keyId: "rzp_test_abc", keySecret: "s" };
  await assert.rejects(readOrderPayments(() => answer(200, {}), credentials, "../secrets"), /not a Razorpay order id/);
  await assert.rejects(readOrderPayments(() => answer(401, {}), credentials, "order_abc"), /HTTP 401/);
});

test("the webhook signature is the hex HMAC-SHA256 of the raw body", () => {
  assert.match(signWebhook("body", "secret"), /^[0-9a-f]{64}$/u);
  assert.notEqual(signWebhook("body", "secret"), signWebhook("body2", "secret"));
  assert.equal(signWebhook("", "key"), "5d5d139563c95b5967b9bd9a8c9b233a9dedb45072794cd232dc1b74832607d0");
});

test("only a registered test user of the development app may continue", async () => {
  const app = { id: "1234567890", secret: "appsecret" };
  const urls: string[] = [];
  const fetchImpl: FetchLike = (url) => {
    urls.push(url);
    return answer(200, { data: [{ id: "tu-1" }, { id: "tu-2" }] });
  };
  await assert.doesNotReject(assertTestUser(fetchImpl, app, "tu-2"));
  await assert.rejects(assertTestUser(fetchImpl, app, "real-user"), MetaModeError);
  assert.match(urls[0], /accounts\/test-users/);
  assert.match(urls[0], /access_token=1234567890%7Cappsecret/);
  await assert.rejects(assertTestUser(() => answer(400, {}), app, "tu-1"), /HTTP 400/);
  await assert.rejects(assertTestUser(() => answer(200, {}), app, "tu-1"), MetaModeError);
});

test("granted and declined Meta permissions are read from Graph", async () => {
  const permissions = await readGrantedPermissions(
    () =>
      answer(200, {
        data: [
          { permission: "pages_manage_posts", status: "granted" },
          { permission: "pages_show_list", status: "granted" },
          { permission: "business_management", status: "declined" },
        ],
      }),
    { id: "1", secret: "s" },
    "tu-1",
  );
  assert.deepEqual(permissions, { granted: ["pages_manage_posts", "pages_show_list"], declined: ["business_management"] });
  assert.deepEqual(await readGrantedPermissions(() => answer(200, {}), { id: "1", secret: "s" }, "tu-1"), { granted: [], declined: [] });
});

test("platform readers find a field at any depth and report a missing one as undefined", () => {
  const body = { data: { relationship: { state: "Trial" } }, list: [{ Status: "CONNECTED", nested: { scopes: ["a"] } }] };
  assert.equal(pick(body, ["lifecycleState", "state"]), "Trial");
  assert.equal(pick(body, ["status"]), "CONNECTED");
  assert.equal(pick(body, ["absent"]), undefined);
  assert.equal(pick("scalar", ["state"]), undefined);
  assert.equal(pick(null, ["state"]), undefined);
});

test("identifiers are collected from payloads and urls in a stable form", () => {
  const id = "7F3A9C2E-0B1D-4E5F-8A6B-1C2D3E4F5A6B";
  assert.deepEqual(collectIdentifiers({ a: id, b: [id.toLowerCase(), "nope"] }), [id.toLowerCase()]);
  assert.deepEqual(collectIdentifiers(`see ${id}`), [id.toLowerCase()]);
  assert.deepEqual(collectIdentifiers(undefined), []);
  assert.equal(relationshipIdFromUrl(`https://x/relationships/${id}/contract`), id.toLowerCase());
  assert.equal(relationshipIdFromUrl("https://x/home"), undefined);
});
