// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

export type PricingKind = 'RATE' | 'PACKAGE' | 'POLICY' | 'GRANT' | 'BUDGET' | 'COUPON';

export type PricingVersion = {
  versionId: string;
  kind: PricingKind;
  subjectKey: string;
  versionNo: number;
  state: string;
  body: Record<string, unknown>;
  bodyDigest: string;
  seed: boolean;
  effectiveFrom: string | null;
  evidenceId: string | null;
  needsSecondConfirmation: boolean;
  createdBy: string;
  createdAt: string;
  authorizedBy?: string | null;
};

export type PricingViolation = { code: string; path: string; message: string };

export type PricingProblem = {
  code?: string;
  title?: string;
  detail?: string;
  status?: number;
  correlationId?: string;
  violations?: PricingViolation[];
  minimumCompliantPricePaise?: number;
  blockingPaise?: number;
  componentId?: string;
};

export type PricingResult<T> =
  | { ok: true; status: number; data: T; etag: string | null }
  | { ok: false; status: number; problem: PricingProblem };

// The version tag the owner compares with expectedVersion: number, state and the first 16 digest characters.
export function versionTag(version: Pick<PricingVersion, 'versionNo' | 'state' | 'bodyDigest'>): string {
  return `${version.versionNo}:${version.state}:${version.bodyDigest.slice(0, 16)}`;
}

export function formatInr(paise: number): string {
  return `INR ${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// Whole paise from an INR amount typed by a person; anything finer than a paisa or not a number is refused.
export function paiseFromInr(text: string): number | null {
  const trimmed = text.trim();
  if (!/^\d{1,12}(\.\d{1,2})?$/.test(trimmed)) return null;
  return Math.round(Number(trimmed) * 100);
}

export function inrFromPaise(paise: unknown): string {
  return typeof paise === 'number' && Number.isFinite(paise) ? (paise / 100).toFixed(2) : '';
}

const problemMessages: Record<string, string> = {
  PRICING_FORBIDDEN: 'Your role may not do this.',
  PRICING_STEP_UP_REQUIRED: 'Confirm your identity again with multi-factor sign-in, then retry.',
  PRICING_DRAFT_INVALID: 'The draft breaks pricing rules. Fix the items listed below.',
  PRICING_BELOW_FLOOR: 'The price is below the cost floor.',
  PRICING_NEEDS_SECOND_CONFIRMATION: 'This change is large. Confirm it a second time to continue.',
  PRICING_ILLEGAL_TRANSITION: 'The version is not in a state that allows this step.',
  PRICING_CEILING_ABOVE_MAXIMUM: 'The ceiling is above the platform maximum.',
  PRICING_CEILING_BELOW_OPEN_RESERVATIONS: 'The ceiling is below what is already reserved or spent.',
  PACKAGE_COMPONENT_NOT_AVAILABLE: 'A package component is not available for this agent.',
  RECIPE_THREAD_NOT_AUTHORIZED: 'A recipe thread is not authorized in the catalogue.',
  PRICING_REQUEST_INVALID: 'The request was not valid. Check the fields and try again.',
  PRICING_NOT_FOUND: 'That pricing version no longer exists.',
  PRICING_VERSION_CONFLICT: 'Someone changed this version. Reload it and try again.',
  PRICING_IDEMPOTENCY_CONFLICT: 'That request key was already used for a different change.',
  PRICING_RATE_LIMITED: 'Too many changes in a minute. Wait and try again.',
  PRICING_UNAVAILABLE: 'Pricing administration is unavailable. Try again shortly.',
};

export function problemText(problem: PricingProblem): string {
  const base = problemMessages[problem.code ?? ''] ?? problemMessages.PRICING_UNAVAILABLE;
  const extras: string[] = [];
  if (typeof problem.minimumCompliantPricePaise === 'number') {
    extras.push(`Lowest compliant price: ${formatInr(problem.minimumCompliantPricePaise)}.`);
  }
  if (typeof problem.blockingPaise === 'number') {
    extras.push(`Already committed: ${formatInr(problem.blockingPaise)}.`);
  }
  if (problem.componentId) extras.push(`Component: ${problem.componentId}.`);
  return [base, ...extras].join(' ');
}

export function subjectKeyFor(kind: Exclude<PricingKind, 'PACKAGE'>, body: Record<string, unknown>): string {
  switch (kind) {
    case 'RATE':
      return `thread:${String(body.threadId)}`;
    case 'POLICY':
      return 'policy:platform';
    case 'GRANT':
      return `grant:${String(body.kind)}|${String(body.agentType)}|${String(body.agentVersion)}`;
    case 'BUDGET':
      return `budget:${String(body.scope)}|${String(body.ref)}`;
    case 'COUPON':
      return `coupon:${String(body.code)}`;
  }
}

export function packageSubjectKey(body: Record<string, unknown>): string {
  return `package:${String(body.agentType)}|${String(body.agentVersion)}|${String(body.packageCode)}`;
}
