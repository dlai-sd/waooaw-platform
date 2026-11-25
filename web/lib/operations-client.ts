'use client';

// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009
// Constitutional basis: C-023, C-049, C-059, C-063

export type OverviewView = {
  environment: string;
  whatsApp: string;
  whatsAppReason?: string | null;
  openSignals: number;
  blockedMessages: number;
  unresolvedMessages: number;
  oldestQueuedMinutes?: number | null;
  oldestBlockedMinutes?: number | null;
  deliveries: Array<{ channel: string; outcome: string; count: number }>;
  services: Array<{ name: string; state: string }>;
  observedAt: string;
};

export type BlockedMessage = {
  outboxId: string;
  relationshipId: string;
  purpose: string;
  templateCategory?: string | null;
  blockedReason?: string | null;
  attemptNumber: number;
  blockedSince: string;
  ageMinutes: number;
};

export type PageRecord = { signal: string; outcome: string; reason?: string | null; recordedAt: string };

export type ResolveAction = 'RETRY' | 'CLOSE_WITH_REASON' | 'MARK_UNDELIVERABLE';

export type OperationsResult<T> =
  | { ok: true; data: T }
  | { ok: false; reason: 'step-up' | 'forbidden' | 'inactive' | 'failed' };

async function call<T>(
  method: 'GET' | 'POST',
  path: string,
  body?: unknown,
  key?: string
): Promise<OperationsResult<T>> {
  let response: Response;
  try {
    response = await fetch(`/api/operations/${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(key ? { 'Idempotency-Key': key } : {}),
      },
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    return { ok: false, reason: 'failed' };
  }
  const payload = (await response.json().catch(() => null)) as { code?: string } | null;
  if (response.status === 403)
    return { ok: false, reason: payload?.code === 'OPERATIONS_STEP_UP_REQUIRED' ? 'step-up' : 'forbidden' };
  if (response.status === 503 && payload?.code === 'OPERATIONS_WHATSAPP_INACTIVE')
    return { ok: false, reason: 'inactive' };
  if (!response.ok) return { ok: false, reason: 'failed' };
  return { ok: true, data: payload as T };
}

export const readOverview = () => call<OverviewView>('GET', 'overview');
export const readBlocked = () => call<{ items: BlockedMessage[] }>('GET', 'blocked-messages');
export const readPages = () => call<{ items: PageRecord[] }>('GET', 'pages');
export type TimelineView = {
  emergencyStopActive: boolean;
  workItems: Array<{
    workItemId: string;
    workItemType: string;
    state: string;
    reasonCode?: string | null;
    sentence: string;
  }>;
};
export const readTimeline = (tenantId: string, relationshipId: string) =>
  call<TimelineView>(
    'GET',
    `relationships/${encodeURIComponent(relationshipId)}/work-timeline?tenantId=${encodeURIComponent(tenantId)}`
  );
export const readSpendChain = (tenantId: string, relationshipId: string) =>
  call<{ authorizations: unknown[]; items: unknown[]; reconciliations: unknown[] }>(
    'GET',
    `relationships/${encodeURIComponent(relationshipId)}/spend-chain?tenantId=${encodeURIComponent(tenantId)}`
  );
export const acknowledgePage = (code: string) =>
  call<{ code: string }>('POST', `pages/${encodeURIComponent(code)}/acknowledge`, {});
export const resolveBlocked = (outboxId: string, action: ResolveAction, reason: string) =>
  call<{ resolutionId: string; replayed: boolean }>(
    'POST',
    `blocked-messages/${encodeURIComponent(outboxId)}/resolve`,
    { schemaVersion: '1.0.0', action, reason },
    crypto.randomUUID()
  );

export const operationsCopy = {
  loadFailed: 'This could not be loaded right now. Nothing was changed.',
  forbidden: 'You do not have access to this view.',
  stepUp: 'This change needs a fresh multi-factor sign-in.',
  inactive: 'WhatsApp is not active in this environment, so there are no messages to show.',
  noBlocked: 'No blocked messages.',
  noPages: 'No pages recorded.',
  resolved: 'Resolved. The message was kept; only its status changed.',
  failed: 'That change could not be completed. Nothing was changed.',
  emitted: 'Handed to monitoring (a person receiving it is not proven here)',
} as const;
