// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md §3 Evidence Baseline And Confidence Rules
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

const storageKey = 'waooaw:auth-transition';

export type AuthTransitionStage =
  | 'ROUTE_REQUESTED'
  | 'ROUTE_RENDERED'
  | 'PROVIDER_PROJECTION_READY'
  | 'BROKER_REDIRECT_REQUESTED'
  | 'SESSION_RESOLVED';

type AuthTransition = { correlationId: string; startedAt: number };

function readTransition(): AuthTransition | undefined {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(storageKey) ?? '') as Partial<AuthTransition>;
    return typeof parsed.correlationId === 'string' && typeof parsed.startedAt === 'number'
      ? { correlationId: parsed.correlationId, startedAt: parsed.startedAt }
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

export function recordAuthTransition(stage: AuthTransitionStage, reasonCode = 'OK'): void {
  const transition = readTransition();
  if (!transition) return;
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
  if (stage === 'SESSION_RESOLVED') sessionStorage.removeItem(storageKey);
}
