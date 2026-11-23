// Implements: adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decisions 1, 2 and 5; architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation), C-065 (Separation of Duties)
import { randomBytes } from "node:crypto";
import { generateOtpSecret } from "./totp.ts";
import type { FetchLike } from "./razorpay.ts";

export class ProvisionerRefusal extends Error {}

export interface ProvisionerConfig {
  identityOrigin: string;
  realm: string;
  clientId: string;
  clientSecret: string;
  usernamePrefix: string;
  emailDomain: string;
  group: string;
}

export interface SyntheticCustomer {
  userId: string;
  username: string;
  email: string;
  password: string;
  otpSecret: string;
}

interface KeycloakUser {
  id: string;
  username: string;
}

/**
 * The client holds realm-wide manage-users, so containment is enforced here (ADR-055 decision 2b): every call is
 * checked against the reserved prefix and the harness refuses to read, change or delete any other user.
 */
export function assertSyntheticUsername(username: string, prefix: string): void {
  if (!username.startsWith(prefix) || username.length <= prefix.length) {
    throw new ProvisionerRefusal(`refusing to touch ${username.slice(0, 4)}…: not a reserved synthetic username`);
  }
}

export function syntheticUsername(prefix: string, runId: string, label: string): string {
  const clean = (value: string): string => value.toLowerCase().replace(/[^a-z0-9]/gu, "");
  return `${prefix}${clean(runId).slice(0, 12)}-${clean(label)}`;
}

export class Provisioner {
  private readonly config: ProvisionerConfig;
  private readonly fetchImpl: FetchLike;
  private token: string | undefined;
  readonly touched: string[] = [];

  constructor(config: ProvisionerConfig, fetchImpl: FetchLike) {
    this.config = config;
    this.fetchImpl = fetchImpl;
  }

  private get admin(): string {
    return `${this.config.identityOrigin}/admin/realms/${this.config.realm}`;
  }

  private async call(method: string, url: string, body?: unknown): Promise<{ status: number; text: string }> {
    const token = await this.accessToken();
    const response = await this.fetchImpl(url, {
      method,
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    return { status: response.status, text: await response.text() };
  }

  /** The provisioning client's own token: it carries the acceptance-provisioner role the internal marker route requires. */
  async serviceToken(): Promise<string> {
    return this.accessToken();
  }

  private async accessToken(): Promise<string> {
    if (this.token !== undefined) {
      return this.token;
    }
    const form = new URLSearchParams({
      grant_type: "client_credentials",
      client_id: this.config.clientId,
      client_secret: this.config.clientSecret,
    });
    const response = await this.fetchImpl(`${this.config.identityOrigin}/realms/${this.config.realm}/protocol/openid-connect/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    const text = await response.text();
    if (!response.ok) {
      throw new ProvisionerRefusal(`provisioning client could not authenticate (HTTP ${response.status})`);
    }
    this.token = (JSON.parse(text) as { access_token: string }).access_token;
    return this.token;
  }

  /** Creates one run-scoped customer: verified synthetic email, generated password, OTP credential, synthetic group. */
  async createCustomer(runId: string, label: string): Promise<SyntheticCustomer> {
    const username = syntheticUsername(this.config.usernamePrefix, runId, label);
    assertSyntheticUsername(username, this.config.usernamePrefix);
    const password = randomBytes(18).toString("base64url");
    const otpSecret = generateOtpSecret();
    const email = `${username}@${this.config.emailDomain}`;
    const created = await this.call("POST", `${this.admin}/users`, {
      username,
      email,
      emailVerified: true,
      enabled: true,
      firstName: "Synthetic",
      lastName: label.toUpperCase(),
      groups: [`/${this.config.group}`],
      credentials: [
        { type: "password", value: password, temporary: false },
        {
          type: "otp",
          secretData: JSON.stringify({ value: otpSecret }),
          credentialData: JSON.stringify({ subType: "totp", digits: 6, period: 30, algorithm: "HmacSHA1", counter: 0 }),
        },
      ],
    });
    if (created.status !== 201) {
      throw new ProvisionerRefusal(`synthetic user was not created (HTTP ${created.status})`);
    }
    const found = await this.findByUsername(username);
    this.touched.push(found.id);
    return { userId: found.id, username, email, password, otpSecret };
  }

  async findByUsername(username: string): Promise<KeycloakUser> {
    assertSyntheticUsername(username, this.config.usernamePrefix);
    const response = await this.call("GET", `${this.admin}/users?username=${encodeURIComponent(username)}&exact=true`);
    const users = JSON.parse(response.text) as KeycloakUser[];
    const user = users.find((candidate) => candidate.username === username);
    if (response.status !== 200 || user === undefined) {
      throw new ProvisionerRefusal("synthetic user could not be read back");
    }
    return user;
  }

  /** Deletes a user only after reading it back and confirming it carries the reserved prefix. */
  async deleteCustomer(userId: string): Promise<void> {
    const read = await this.call("GET", `${this.admin}/users/${encodeURIComponent(userId)}`);
    if (read.status === 404) {
      return;
    }
    const user = JSON.parse(read.text) as KeycloakUser;
    assertSyntheticUsername(user.username, this.config.usernamePrefix);
    const deleted = await this.call("DELETE", `${this.admin}/users/${encodeURIComponent(userId)}`);
    if (deleted.status !== 204 && deleted.status !== 404) {
      throw new ProvisionerRefusal(`synthetic user was not deleted (HTTP ${deleted.status})`);
    }
  }

  /** Members of the synthetic group that still exist, for the cleanup guarantee (F13). */
  async listSyntheticUsers(): Promise<KeycloakUser[]> {
    const groups = await this.call("GET", `${this.admin}/groups?search=${encodeURIComponent(this.config.group)}&exact=true`);
    const group = (JSON.parse(groups.text) as { id: string; name: string }[]).find((item) => item.name === this.config.group);
    if (group === undefined) {
      return [];
    }
    const members = await this.call("GET", `${this.admin}/groups/${group.id}/members?first=0&max=500`);
    return (JSON.parse(members.text) as KeycloakUser[]).filter((user) => user.username.startsWith(this.config.usernamePrefix));
  }

  /** Removes every reserved-prefix user left in the synthetic group, never anything else. */
  async removeAllSynthetic(): Promise<string[]> {
    const users = await this.listSyntheticUsers();
    for (const user of users) {
      await this.deleteCustomer(user.id);
    }
    return users.map((user) => user.id);
  }

  /**
   * Post-run audit (F18): the provisioning client's admin events must show no user change outside the reserved prefix.
   * Resource paths are users/<id>; every id must be one this run created or listed as synthetic.
   */
  async outsideTouches(sinceIso: string, knownSyntheticIds: string[]): Promise<string[]> {
    const response = await this.call(
      "GET",
      `${this.admin}/admin-events?resourceTypes=USER&authClient=${encodeURIComponent(this.config.clientId)}&dateFrom=${encodeURIComponent(sinceIso.slice(0, 10))}&max=500`,
    );
    if (response.status !== 200) {
      throw new ProvisionerRefusal(`admin events could not be read (HTTP ${response.status})`);
    }
    const events = JSON.parse(response.text) as { resourcePath?: string; time?: number }[];
    const since = Date.parse(sinceIso);
    const known = new Set(knownSyntheticIds);
    return events
      .filter((event) => (event.time ?? 0) >= since)
      .map((event) => /^users\/([^/]+)/u.exec(event.resourcePath ?? "")?.[1])
      .filter((id): id is string => id !== undefined && !known.has(id));
  }
}
