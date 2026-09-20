// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md §3 Evidence Baseline And Confidence Rules
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

const storageKey = 'waooaw:auth-transition';

export type AuthTransitionStage =
  | 'ROUTE_REQUESTED'
  | 'ROUTE_RENDERED'
  | 'PROVIDER_PROJECTION_READY'
  | 'BROKER_REDIRECT_REQUESTED'
  | 'PROVIDER_CANCELLED'
  | 'BROKER_LAUNCH_FAILED'
  | 'CALLBACK_FAILED'
  | 'ACCOUNT_SWITCH_REQUESTED'
  | 'ACCOUNT_SWITCH_COMPLETED'
  | 'ACCOUNT_SWITCH_FAILED'
  | 'SESSION_RESOLVED';

type AuthTransition = { correlationId: string; startedAt: number; providerClass?: string };

function readTransition(): AuthTransition | undefined {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(storageKey) ?? '') as Partial<AuthTransition>;
    return typeof parsed.correlationId === 'string' && typeof parsed.startedAt === 'number'
      ? { correlationId: parsed.correlationId, startedAt: parsed.startedAt, providerClass: parsed.providerClass }
      : undefined;
  } catch {
    return undefined;
  }
}

export function beginAuthTransition(): string {
  const transition = { correlationId: crypto.randomUUID(), startedAt: performance.now() };
  sessionStorage.setItem(storageKey, JSON.stringify(transition));
  recordAuthTransition('ROUTE_REQUESTED');
  return transition.correlationId;
}

export function recordAuthTransition(stage: AuthTransitionStage, reasonCode = 'OK', providerClass?: string): void {
  const transition = readTransition();
  if (!transition) return;
  if (providerClass) {
    transition.providerClass = providerClass;
    sessionStorage.setItem(storageKey, JSON.stringify(transition));
  }
  window.dispatchEvent(
    new CustomEvent('waooaw:auth-transition', {
      detail: {
        correlationId: transition.correlationId,
        durationMs: Math.max(0, performance.now() - transition.startedAt),
        reasonCode,
        stage,
      },
    })
  );
  if (
    ['ROUTE_REQUESTED', 'BROKER_REDIRECT_REQUESTED', 'PROVIDER_CANCELLED', 'BROKER_LAUNCH_FAILED', 'CALLBACK_FAILED', 'ACCOUNT_SWITCH_REQUESTED', 'ACCOUNT_SWITCH_COMPLETED', 'ACCOUNT_SWITCH_FAILED', 'SESSION_RESOLVED'].includes(stage) &&
    typeof fetch === 'function'
  ) {
    void fetch('/api/auth/identity-events', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        correlationId: transition.correlationId,
        stage,
        providerClass: providerClass ?? transition.providerClass ?? 'UNKNOWN',
      }),
      keepalive: true,
    }).catch(() => undefined);
  }
  if (stage === 'SESSION_RESOLVED' || stage === 'CALLBACK_FAILED') sessionStorage.removeItem(storageKey);
}
