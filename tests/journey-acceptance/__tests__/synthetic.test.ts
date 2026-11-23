// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5, §7
// Constitutional basis: C-059 (Implementation Traceability)
import assert from "node:assert/strict";
import { test } from "node:test";
import { Provisioner, ProvisionerRefusal, assertSyntheticUsername, syntheticUsername } from "../lib/keycloak.ts";
import type { ProvisionerConfig } from "../lib/keycloak.ts";
import { MarkerRefusal, deactivateRun, registerSandboxRecipient, registerSyntheticSubject } from "../lib/marker.ts";
import { base32Decode, base32Encode, generateOtpSecret, totp } from "../lib/totp.ts";
import type { FetchLike } from "../lib/razorpay.ts";

const config: ProvisionerConfig = {
  identityOrigin: "https://auth.example",
  realm: "waooaw",
  clientId: "waooaw-acceptance-provisioner",
  clientSecret: "client-secret-value",
  usernamePrefix: "acc-",
  emailDomain: "synthetic.waooaw.test",
  group: "synthetic",
};

interface Call {
  method: string;
  url: string;
  body?: string;
}

function respond(status: number, body: unknown = ""): { ok: boolean; status: number; text(): Promise<string> } {
  return { ok: status >= 200 && status < 300, status, text: async () => (typeof body === "string" ? body : JSON.stringify(body)) };
}

/** A tiny in-memory Keycloak: enough of the admin API to prove containment rules. */
function keycloak(initial: { id: string; username: string }[] = []): { fetchImpl: FetchLike; calls: Call[]; users: Map<string, string>; events: unknown[] } {
  const users = new Map(initial.map((user) => [user.id, user.username]));
  const calls: Call[] = [];
  const events: unknown[] = [];
  let sequence = 0;
  const fetchImpl: FetchLike = async (url, init) => {
    const method = init?.method ?? "GET";
    calls.push({ method, url, body: init?.body });
    if (url.endsWith("/protocol/openid-connect/token")) {
      return respond(200, { access_token: "service-token" });
    }
    const path = url.replace("https://auth.example/admin/realms/waooaw", "");
    if (method === "POST" && path === "/users") {
      sequence += 1;
      const body = JSON.parse(init?.body ?? "{}") as { username: string };
      users.set(`user-${sequence}`, body.username);
      return respond(201);
    }
    if (method === "GET" && path.startsWith("/users?")) {
      const wanted = new URL(url).searchParams.get("username");
      return respond(200, [...users].filter(([, name]) => name === wanted).map(([id, username]) => ({ id, username })));
    }
    const single = /^\/users\/([^/?]+)$/u.exec(path);
    if (single !== null && method === "GET") {
      const name = users.get(single[1]);
      return name === undefined ? respond(404) : respond(200, { id: single[1], username: name });
    }
    if (single !== null && method === "DELETE") {
      return users.delete(single[1]) ? respond(204) : respond(404);
    }
    if (path.startsWith("/groups?")) {
      return respond(200, [{ id: "group-1", name: "synthetic" }]);
    }
    if (path.startsWith("/groups/group-1/members")) {
      return respond(200, [...users].map(([id, username]) => ({ id, username })));
    }
    if (path.startsWith("/admin-events")) {
      return respond(200, events);
    }
    return respond(500);
  };
  return { fetchImpl, calls, users, events };
}

test("RFC 6238 test vectors and base32 round-trip", () => {
  const secret = base32Encode(Buffer.from("12345678901234567890"));
  assert.equal(secret, ["GEZDGNBV", "GY3TQOJQ", "GEZDGNBV", "GY3TQOJQ"].join(""));
  assert.equal(totp(secret, 59_000), "287082");
  assert.equal(totp(secret, 1_111_111_109_000), "081804");
  assert.equal(base32Decode(secret).toString(), "12345678901234567890");
  assert.throws(() => base32Decode("not*base32"));
  assert.match(generateOtpSecret(), /^[A-Z2-7]{32}$/u);
  assert.equal(base32Encode(Buffer.from([0xff])), "74");
});

test("only reserved-prefix usernames are ever accepted", () => {
  assert.equal(syntheticUsername("acc-", "Run-ID_123456789012345", "A"), "acc-runid1234567-a");
  assert.doesNotThrow(() => assertSyntheticUsername("acc-run1-a", "acc-"));
  for (const bad of ["founder@waooaw.local", "acc-", "customer-acc-1"]) {
    assert.throws(() => assertSyntheticUsername(bad, "acc-"), ProvisionerRefusal);
  }
});

test("a created customer is verified, in the synthetic group, with a password and an OTP credential", async () => {
  const { fetchImpl, calls } = keycloak();
  const provisioner = new Provisioner(config, fetchImpl);
  const customer = await provisioner.createCustomer("run-0123456789", "a");
  const create = JSON.parse(calls.find((call) => call.method === "POST" && call.url.endsWith("/users"))?.body ?? "{}");
  assert.equal(create.emailVerified, true);
  assert.deepEqual(create.groups, ["/synthetic"]);
  assert.equal(create.email, `${customer.username}@synthetic.waooaw.test`);
  assert.equal(create.credentials[0].type, "password");
  assert.equal(create.credentials[1].type, "otp");
  assert.equal(JSON.parse(create.credentials[1].secretData).value, customer.otpSecret);
  assert.ok(customer.password.length >= 20);
  assert.ok(customer.username.startsWith("acc-"));
});

test("the provisioner refuses to delete or read any user outside the reserved prefix", async () => {
  const { fetchImpl, calls, users } = keycloak([{ id: "real-1", username: "founder@waooaw.local" }]);
  const provisioner = new Provisioner(config, fetchImpl);
  await assert.rejects(provisioner.deleteCustomer("real-1"), ProvisionerRefusal);
  await assert.rejects(provisioner.findByUsername("founder@waooaw.local"), ProvisionerRefusal);
  assert.ok(users.has("real-1"));
  assert.ok(!calls.some((call) => call.method === "DELETE"));
});

test("cleanup removes every reserved-prefix member of the synthetic group and nothing else", async () => {
  const { fetchImpl, users } = keycloak([
    { id: "u1", username: "acc-old-a" },
    { id: "u2", username: "acc-old-b" },
    { id: "real-1", username: "founder@waooaw.local" },
  ]);
  const provisioner = new Provisioner(config, fetchImpl);
  assert.deepEqual(await provisioner.removeAllSynthetic(), ["u1", "u2"]);
  assert.deepEqual([...users.keys()], ["real-1"]);
  await provisioner.deleteCustomer("already-gone");
});

test("the admin-event audit reports any user touched that this run does not own", async () => {
  const state = keycloak();
  const provisioner = new Provisioner(config, state.fetchImpl);
  const since = "2026-11-23T10:00:00.000Z";
  state.events.push(
    { resourcePath: "users/user-1", time: Date.parse(since) + 1000 },
    { resourcePath: "users/real-1", time: Date.parse(since) + 2000 },
    { resourcePath: "users/real-2", time: Date.parse(since) - 5000 },
    { resourcePath: "groups/x", time: Date.parse(since) + 3000 },
  );
  assert.deepEqual(await provisioner.outsideTouches(since, ["user-1"]), ["real-1"]);
  const failing: FetchLike = async (url) => (url.endsWith("/token") ? respond(200, { access_token: "t" }) : respond(403));
  await assert.rejects(new Provisioner(config, failing).outsideTouches(since, []), ProvisionerRefusal);
});

test("authentication and creation failures stop the run", async () => {
  const noAuth: FetchLike = async () => respond(401);
  await assert.rejects(new Provisioner(config, noAuth).createCustomer("run-0123456789", "a"), /could not authenticate/);
  const rejecting: FetchLike = async (url) => (url.endsWith("/token") ? respond(200, { access_token: "t" }) : respond(409));
  await assert.rejects(new Provisioner(config, rejecting).createCustomer("run-0123456789", "a"), /was not created/);
  const missing: FetchLike = async (url, init) => {
    if (url.endsWith("/token")) return respond(200, { access_token: "t" });
    return init?.method === "POST" ? respond(201) : respond(200, []);
  };
  await assert.rejects(new Provisioner(config, missing).createCustomer("run-0123456789", "a"), /read back/);
  const noDelete: FetchLike = async (url, init) => {
    if (url.endsWith("/token")) return respond(200, { access_token: "t" });
    return init?.method === "DELETE" ? respond(500) : respond(200, { id: "u1", username: "acc-x" });
  };
  await assert.rejects(new Provisioner(config, noDelete).deleteCustomer("u1"), /was not deleted/);
  const noGroup: FetchLike = async (url) => (url.endsWith("/token") ? respond(200, { access_token: "t" }) : respond(200, []));
  assert.deepEqual(await new Provisioner(config, noGroup).listSyntheticUsers(), []);
});

test("marker registration carries the provisioner token, the run id and only the subject", async () => {
  const calls: Call[] = [];
  const ok: FetchLike = async (url, init) => {
    calls.push({ method: init?.method ?? "GET", url, body: init?.body });
    return respond(201);
  };
  await registerSyntheticSubject(ok, "https://api.example", "tok", "run-0123456789", "kc-sub-0001");
  await registerSandboxRecipient(ok, "https://api.example", "tok", "run-0123456789", "+15550001111");
  await deactivateRun(ok, "https://api.example", "tok", "run-0123456789");
  assert.deepEqual(
    calls.map((call) => `${call.method} ${call.url}`),
    [
      "POST https://api.example/internal/v1/acceptance/runs/run-0123456789/synthetic-subjects",
      "PUT https://api.example/internal/v1/acceptance/runs/run-0123456789/sandbox-recipients",
      "DELETE https://api.example/internal/v1/acceptance/runs/run-0123456789",
    ],
  );
  assert.equal(calls[0].body, JSON.stringify({ subject: "kc-sub-0001" }));
});

test("a refused marker registration stops the run before any customer acts", async () => {
  const refused: FetchLike = async () => respond(403);
  await assert.rejects(registerSyntheticSubject(refused, "https://api.example", "t", "run-0123456789", "kc-sub-0001"), MarkerRefusal);
  await assert.rejects(registerSandboxRecipient(refused, "https://api.example", "t", "run-0123456789", "+1555"), MarkerRefusal);
  await assert.rejects(deactivateRun(refused, "https://api.example", "t", "run-0123456789"), MarkerRefusal);
  const noContent: FetchLike = async () => respond(204);
  await registerSyntheticSubject(noContent, "https://api.example", "t", "run-0123456789", "kc-sub-0001");
});
