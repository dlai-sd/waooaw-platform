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
  reasonText: string;
  canUnblock: boolean;
  attemptNumber: number;
  blockedSince: string;
  ageMinutes: number;
};

export type ResolutionRecord = {
  resolutionId: string;
  outboxId: string;
  action: ResolveAction;
  reason: string;
  resolvedBy: string;
  resolvedAt: string;
};

export type PageRecord = {
  signal: string;
  outcome: string;
  reason?: string | null;
  count: number;
  firstRecordedAt: string;
  recordedAt: string;
};

export type CustomerStatus = 'LOGGED_IN_ONLY' | 'REGISTRATION_STARTED' | 'REGISTERED';

export type CustomerEntry = {
  registrationId: string;
  displayName?: string | null;
  maskedEmail?: string | null;
  maskedMobile?: string | null;
  status: CustomerStatus;
  registrationState: string;
  firstSeenAt: string;
  lastActiveAt: string;
  registeredAt?: string | null;
};

export type CustomerFilters = { name?: string; contact?: string; status?: CustomerStatus | ''; cursor?: string };

export type ResolveAction = 'RETRY' | 'CLOSE_WITH_REASON' | 'MARK_UNDELIVERABLE';

export type OperationsResult<T> =
  | { ok: true; data: T }
  | { ok: false; reason: 'step-up' | 'forbidden' | 'inactive' | 'failed'; code?: string };

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
  if (!response.ok) return { ok: false, reason: 'failed', code: payload?.code };
  return { ok: true, data: payload as T };
}

export const readOverview = () => call<OverviewView>('GET', 'overview');
export const readBlocked = () => call<{ items: BlockedMessage[] }>('GET', 'blocked-messages');
export const readPages = () => call<{ items: PageRecord[] }>('GET', 'pages');
export const readResolutions = () => call<{ items: ResolutionRecord[] }>('GET', 'blocked-messages/history');
export const readCustomers = (filters: CustomerFilters) => {
  const query = new URLSearchParams({ pageSize: '10' });
  if (filters.name?.trim()) query.set('name', filters.name.trim());
  if (filters.contact?.trim()) query.set('contact', filters.contact.trim());
  if (filters.status) query.set('status', filters.status);
  if (filters.cursor) query.set('cursor', filters.cursor);
  return call<{ items: CustomerEntry[]; nextCursor?: string | null }>('GET', `customers?${query.toString()}`);
};
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
  noCustomers: 'No customers match these filters.',
  stepUpResume: 'Confirm below and your action resumes automatically.',
  loading: 'Loading…',
  retryLoad: 'Retry',
  resolved:
    'Done. The message was kept; only its status changed, and your name, the time and the reason were recorded.',
  retryQueued: 'Queued for retry. Delivery is confirmed when the message leaves this list — refresh to check.',
  retryFailed: 'The message could not be queued for retry. Nothing was changed.',
  retryInactive: 'WhatsApp is not active in this environment, so the message cannot be retried. Nothing was changed.',
  spendChainFailed: 'The spend chain could not be read right now.',
  spendChainUnavailable: 'The spend chain could not be read: the billing engine did not answer.',
  spendChainGrant: 'The spend chain cannot be read yet: it needs a route grant to the billing engine.',
  failed: 'That change could not be completed. Nothing was changed.',
  emitted: 'Handed to monitoring (a person receiving it is not proven here)',
} as const;
