'use client';

// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R007
// Constitutional basis: C-001, C-042, C-049, C-059, C-063

export type InboxAlert = {
  alertId: string;
  version: string;
  alertClass: 'FLOOR' | 'ACTION_REQUIRED' | 'AT_RISK' | 'INFORMATION' | 'OPERATIONS';
  category: string;
  severity: string;
  source: string;
  relationshipId?: string | null;
  occurredAt: string;
  dueMeaning?: string | null;
  readState: 'UNREAD' | 'READ' | 'ACKNOWLEDGED';
  snoozedUntil?: string | null;
  mutable: boolean;
  destination: { surface: string; relationshipId?: string | null; subjectId?: string | null };
  availableAction?: string | null;
};

export type CategoryMute = { category: string; muted: boolean };

export type Categories = { floorCategories: string[]; items: CategoryMute[] };

export type ControlResult<T> = { ok: true; data: T } | { ok: false; reason: 'not-mutable' | 'failed' };

async function call<T>(method: 'GET' | 'POST' | 'PUT', path: string, body?: unknown): Promise<ControlResult<T>> {
  let response: Response;
  try {
    response = await fetch(`/api/alert-controls/${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    return { ok: false, reason: 'failed' };
  }
  if (response.status === 409) return { ok: false, reason: 'not-mutable' };
  if (!response.ok) return { ok: false, reason: 'failed' };
  return { ok: true, data: (await response.json()) as T };
}

export function listInbox(relationshipId?: string): Promise<ControlResult<{ items: InboxAlert[] }>> {
  const query = relationshipId ? `?relationshipId=${encodeURIComponent(relationshipId)}` : '';
  return call('GET', `alerts${query}`);
}

export function snoozeAlert(alert: InboxAlert, until: Date): Promise<ControlResult<InboxAlert>> {
  return call('POST', `alerts/${encodeURIComponent(alert.alertId)}/snooze`, {
    schemaVersion: '1.0.0',
    expectedAlertVersion: alert.version,
    until: until.toISOString(),
  });
}

export function listCategories(): Promise<ControlResult<Categories>> {
  return call('GET', 'categories');
}

export function setCategoryMute(category: string, muted: boolean): Promise<ControlResult<CategoryMute>> {
  return call('PUT', `categories/${encodeURIComponent(category)}`, { schemaVersion: '1.0.0', muted });
}

// An alert opens the surface it is about: a decision opens Decisions, anything about a relationship opens its overview.
export function alertHref(alert: Pick<InboxAlert, 'destination' | 'relationshipId' | 'alertClass'>): string {
  const relationshipId = alert.destination.relationshipId ?? alert.relationshipId;
  if (relationshipId) {
    const surface = alert.alertClass === 'ACTION_REQUIRED' || alert.alertClass === 'FLOOR' ? 'decisions' : 'overview';
    return `/relationships/${encodeURIComponent(relationshipId)}?surface=${surface}`;
  }
  const routes: Record<string, string> = {
    MARKETPLACE: '/marketplace',
    ALERTS: '/alerts',
    BILLING: '/profile',
    PROFILE: '/profile',
    SETTINGS: '/settings',
  };
  return routes[alert.destination.surface] ?? '/home';
}

export const alertControlsCopy = {
  filterLabel: 'Show alerts for',
  allAgents: 'All agents',
  empty: 'No alerts.',
  loadFailed: 'Alerts could not be loaded right now. Nothing was changed.',
  snooze: 'Snooze for a day',
  snoozed: 'Snoozed',
  acknowledge: 'Acknowledge',
  open: 'Open',
  cannotMute: 'This kind of alert can never be switched off.',
  mutedSection: 'Messages to your phone',
  mutedHelp: 'Turn off messages to your phone for a kind of alert. They still appear here.',
  floorNote: 'Emergency Stop, authority and safety alerts always reach you.',
  failed: 'That change could not be completed.',
  classes: {
    FLOOR: 'Always shown',
    ACTION_REQUIRED: 'Needs you',
    AT_RISK: 'At risk',
    INFORMATION: 'For information',
    OPERATIONS: 'Operations',
  } as Record<string, string>,
} as const;
