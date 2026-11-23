// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §3 Components (Guards)
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import type { Finding } from "./types.ts";

export interface SecretPattern {
  kind: string;
  pattern: RegExp;
}

export const SECRET_PATTERNS: SecretPattern[] = [
  { kind: "jwt", pattern: /eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}/ },
  { kind: "bearer-token", pattern: /\bBearer\s+[A-Za-z0-9._~+/=-]{20,}/i },
  { kind: "private-key", pattern: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/ },
  { kind: "razorpay-live-key", pattern: /\brzp_live_[A-Za-z0-9]{6,}/ },
  { kind: "meta-access-token", pattern: /\bEAA[A-Za-z0-9]{30,}/ },
  { kind: "azure-account-key", pattern: /AccountKey=[A-Za-z0-9+/=]{20,}/ },
  {
    kind: "token-field",
    pattern: /["']?(?:access_token|refresh_token|id_token|client_secret|password)["']?\s*[:=]\s*["'][^"']{12,}["']/i,
  },
];

export function scanText(text: string, patterns: SecretPattern[] = SECRET_PATTERNS): string[] {
  return patterns.filter(({ pattern }) => pattern.test(text)).map(({ kind }) => kind);
}

export function secretFindings(where: string, text: string): Finding[] {
  return scanText(text).map((kind) => ({
    guard: "secret_or_token_pattern",
    where,
    detail: `${kind} pattern present; value withheld`,
  }));
}

/** Customer B's identifiers must never appear in anything customer A can read (AD-004, ADR-003). */
export function foreignIdentifierFindings(where: string, text: string, foreignIdentifiers: string[]): Finding[] {
  return foreignIdentifiers
    .filter((identifier) => identifier.length >= 6 && text.includes(identifier))
    .map((identifier) => ({
      guard: "foreign_tenant_identifier",
      where,
      detail: `a customer B identifier (${identifier.slice(0, 3)}…) appears in a customer A response`,
    }));
}

const EMAIL = /[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})/g;
const PHONE = /(?<![\w.])\+\d{10,14}(?![\w.])/;

/** Only synthetic-domain emails and the product's own domains may appear; any other personal datum is a leak (C-063). */
export function personalDataFindings(where: string, text: string, allowedEmailDomains: string[]): Finding[] {
  const findings: Finding[] = [];
  for (const match of text.matchAll(EMAIL)) {
    const domain = match[1].toLowerCase();
    if (!allowedEmailDomains.some((allowed) => domain === allowed || domain.endsWith(`.${allowed}`))) {
      findings.push({
        guard: "personal_data_leakage",
        where,
        detail: `email on non-synthetic domain ${domain}`,
      });
    }
  }
  if (PHONE.test(text)) {
    findings.push({ guard: "personal_data_leakage", where, detail: "phone-number-like value present" });
  }
  return findings;
}

export interface AxeViolation {
  id: string;
  impact?: string | null;
  nodes?: unknown[];
}

/** WCAG 2.1 AA: serious and critical axe violations are findings; the caller runs axe with the wcag2a/wcag2aa/wcag21a/wcag21aa tags. */
export function accessibilityFindings(where: string, violations: AxeViolation[]): Finding[] {
  return violations
    .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
    .map((violation) => ({
      guard: "wcag_2_1_aa",
      where,
      detail: `${violation.id} (${violation.impact}) on ${violation.nodes?.length ?? 0} node(s)`,
    }));
}

export function emergencyStopFindings(where: string, snapshot: { present: boolean; visible: boolean }): Finding[] {
  return snapshot.present && snapshot.visible
    ? []
    : [{ guard: "emergency_stop_reachable", where, detail: "Emergency Stop control is not reachable on this page" }];
}

export interface GuardConfig {
  foreignIdentifiers: () => string[];
  allowedEmailDomains: string[];
}

/** Always-on detector: every page body and API response of the actor passes through `observe`. */
export class Guards {
  private readonly collected: Finding[] = [];
  private readonly config: GuardConfig;

  constructor(config: GuardConfig) {
    this.config = config;
  }

  observe(where: string, text: string): void {
    this.collected.push(
      ...secretFindings(where, text),
      ...foreignIdentifierFindings(where, text, this.config.foreignIdentifiers()),
      ...personalDataFindings(where, text, this.config.allowedEmailDomains),
    );
  }

  record(findings: Finding[]): void {
    this.collected.push(...findings);
  }

  findings(): Finding[] {
    return [...this.collected];
  }
}
