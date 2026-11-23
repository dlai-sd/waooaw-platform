// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §4 Run Lifecycle (steps 1, 5, 6, 7), §5
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { appendFileSync, chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { APIResponse, Browser, BrowserContext, Page } from "@playwright/test";
import { Guards } from "../../lib/guards.ts";
import { Provisioner } from "../../lib/keycloak.ts";
import type { SyntheticCustomer } from "../../lib/keycloak.ts";
import { registerSyntheticSubject } from "../../lib/marker.ts";
import { loadCompiledPlan } from "../../lib/plan.ts";
import type { Plan } from "../../lib/plan.ts";
import { registerLiteral } from "../../lib/private-store.ts";
import type { FetchLike } from "../../lib/razorpay.ts";
import { recordFindings } from "../../lib/step.ts";

export interface Profile {
  environment: string;
  origins: { web: string; api: string; identity: string };
  keycloak: { realm: string; synthetic_group: string; username_prefix: string; email_domain: string };
  sandbox: { razorpay_key_id_prefix: string };
  synthetic: { max_open_relationships: number };
}

export type Label = "A" | "B";

interface RunState {
  runId: string;
  startedAt: string;
  customers: Partial<Record<Label, SyntheticCustomer>>;
  provisioningError?: string;
  values: Record<string, string>;
}

const MAX_RECENT = 200;
const MAX_BODY = 200_000;

export function environment(name: string): string | undefined {
  const value = process.env[name];
  return value !== undefined && value !== "" ? value : undefined;
}

export class Run {
  readonly out: string;
  readonly privateDir: string;
  readonly plan: Plan;
  readonly profile: Profile;
  readonly recent: string[] = [];
  readonly foreignIds: string[] = [];
  readonly fetchImpl: FetchLike = (url, init) => fetch(url, init) as ReturnType<FetchLike>;
  state: RunState;

  constructor() {
    this.out = process.env.ACCEPTANCE_OUT ?? "/out";
    this.privateDir = process.env.ACCEPTANCE_PRIVATE ?? "/private";
    this.plan = loadCompiledPlan(join(this.out, "plan.json")).plan;
    this.profile = JSON.parse(readFileSync(join(this.out, "profile.json"), "utf8")) as Profile;
    mkdirSync(this.privateDir, { recursive: true });
    const stateFile = join(this.privateDir, "run-state.json");
    this.state = existsSync(stateFile)
      ? (JSON.parse(readFileSync(stateFile, "utf8")) as RunState)
      : {
          runId: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`,
          startedAt: new Date().toISOString(),
          customers: {},
          values: {},
        };
  }

  save(): void {
    const stateFile = join(this.privateDir, "run-state.json");
    writeFileSync(stateFile, JSON.stringify(this.state));
    chmodSync(stateFile, 0o600);
  }

  value(key: string): string | undefined {
    return this.state.values[key];
  }

  setValue(key: string, value: string): void {
    this.state.values[key] = value;
    this.save();
  }

  provisioner(): Provisioner | undefined {
    const secret = environment("ACCEPTANCE_KEYCLOAK_PROVISIONER_CLIENT_SECRET");
    if (secret === undefined) {
      return undefined;
    }
    return new Provisioner(
      {
        identityOrigin: this.profile.origins.identity,
        realm: this.profile.keycloak.realm,
        clientId: "waooaw-acceptance-provisioner",
        clientSecret: secret,
        usernamePrefix: this.profile.keycloak.username_prefix,
        emailDomain: this.profile.keycloak.email_domain,
        group: this.profile.keycloak.synthetic_group,
      },
      this.fetchImpl,
    );
  }

  /** Creates customers A and B and registers both as synthetic before either logs in (ADR-055 decisions 1 and 4). */
  async provision(): Promise<string | undefined> {
    if (this.state.customers.A !== undefined && this.state.customers.B !== undefined) {
      return undefined;
    }
    if (this.state.provisioningError !== undefined) {
      return this.state.provisioningError;
    }
    const provisioner = this.provisioner();
    if (provisioner === undefined) {
      return this.fail("the acceptance provisioner secret is not readable, so no synthetic customer can be created");
    }
    try {
      const token = await provisioner.serviceToken();
      for (const label of ["A", "B"] as const) {
        const customer = await provisioner.createCustomer(this.state.runId, label.toLowerCase());
        registerLiteral(this.privateDir, customer.password);
        registerLiteral(this.privateDir, customer.otpSecret);
        this.state.customers[label] = customer;
        this.save();
        await registerSyntheticSubject(this.fetchImpl, this.profile.origins.api, token, this.state.runId, customer.userId);
      }
    } catch (error) {
      await this.removeCustomers();
      return this.fail(error instanceof Error ? error.message : String(error));
    }
    return undefined;
  }

  private fail(message: string): string {
    this.state.provisioningError = message;
    this.save();
    return message;
  }

  async removeCustomers(): Promise<number> {
    const provisioner = this.provisioner();
    let removed = 0;
    if (provisioner === undefined) {
      return removed;
    }
    for (const customer of Object.values(this.state.customers)) {
      if (customer !== undefined) {
        await provisioner.deleteCustomer(customer.userId);
        removed += 1;
      }
    }
    return removed;
  }

  /** Every page and response the customer can read passes through the always-on guards and a redacted network log. */
  observe(context: BrowserContext, label: Label): void {
    context.on("response", async (response) => {
      const url = new URL(response.url());
      appendFileSync(
        join(this.out, "network.jsonl"),
        `${JSON.stringify({ customer: label, method: response.request().method(), path: url.pathname, status: response.status() })}\n`,
      );
      const type = response.headers()["content-type"] ?? "";
      if (!/json|text|html/u.test(type) || url.hostname.endsWith("razorpay.com")) {
        return;
      }
      try {
        const body = (await response.text()).slice(0, MAX_BODY);
        if (label === "A") {
          this.recent.push(body);
          if (this.recent.length > MAX_RECENT) {
            this.recent.shift();
          }
        }
        const guards = new Guards({
          foreignIdentifiers: () => (label === "A" ? this.foreignIds : []),
          allowedEmailDomains: [this.profile.keycloak.email_domain, "waooaw.com"],
        });
        guards.observe(`${label} ${response.request().method()} ${url.pathname}`, body);
        recordFindings(this.out, guards.findings());
      } catch {
        // Redirects and aborted requests have no readable body.
      }
    });
  }

  async context(browser: Browser, label: Label): Promise<BrowserContext> {
    const stateFile = join(this.privateDir, `session-${label}.json`);
    const context = await browser.newContext({
      baseURL: this.profile.origins.web,
      storageState: existsSync(stateFile) ? stateFile : undefined,
    });
    this.observe(context, label);
    return context;
  }

  async saveSession(context: BrowserContext, label: Label): Promise<void> {
    const stateFile = join(this.privateDir, `session-${label}.json`);
    await context.storageState({ path: stateFile });
    chmodSync(stateFile, 0o600);
  }

  /** W2: a read-only GET through the web application's same-origin server route, under the customer's own session. */
  async platform(page: Page, path: string): Promise<{ status: number; json?: unknown }> {
    const response: APIResponse = await page.request.get(`${this.profile.origins.web}${path}`, { failOnStatusCode: false });
    let json: unknown;
    try {
      json = await response.json();
    } catch {
      json = undefined;
    }
    return { status: response.status(), json };
  }
}

let current: Run | undefined;

export function getRun(): Run {
  current ??= new Run();
  return current;
}
