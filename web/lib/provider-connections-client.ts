// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R009, WC149-R010
// Constitutional basis: C-026, C-059, C-063, C-083

export type ConnectionStatus = 'CONNECTED' | 'NEEDS_REPAIR' | 'REVOKED';

export type ProviderConnection = {
  id: string;
  provider: 'meta';
  status: ConnectionStatus;
  accountName: string | null;
  accountId: string | null;
  scopes: string[];
  expiresAt: string | null;
  connectedAt: string | null;
};

export type ConnectionStart = { authorizationUrl: string; expiresAt: string };
export type PublishResult = { providerPostId: string; publishedAt: string };

export type ConnectionProblem = { code?: string; title?: string; status?: number; correlationId?: string };

export type ConnectionResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; problem: ConnectionProblem };

export const maximumPostLength = 2000;

export const statusLabel: Record<ConnectionStatus, string> = {
  CONNECTED: 'Connected',
  NEEDS_REPAIR: 'Needs repair',
  REVOKED: 'Revoked',
};

export const statusExplanation: Record<ConnectionStatus, string> = {
  CONNECTED: 'WAOOAW can publish posts to your Facebook Page, but only the exact posts you approve.',
  NEEDS_REPAIR: 'The access has expired or was withdrawn on Facebook. Reconnect to approve and publish posts again.',
  REVOKED: 'You revoked this connection. WAOOAW deleted its access and cannot use it any more.',
};

const problemMessages: Record<string, string> = {
  CONNECTION_NEEDS_REPAIR: 'Your Facebook connection needs to be reconnected before WAOOAW can publish.',
  CONNECTION_NOT_FOUND: 'That connection no longer exists. The list has been refreshed.',
  CONNECTION_REVOKED: 'That connection was revoked. Connect Facebook again to publish.',
  CONNECTION_FORBIDDEN: 'You are not permitted to manage this connection.',
  CONNECTION_INVALID: 'The request was not valid. Check the post text and try again. Nothing was published.',
  CONNECTION_RATE_LIMITED: 'Too many requests in a minute. Wait and try again.',
  CONNECTION_UNAVAILABLE: 'Connections are temporarily unavailable. Nothing was changed. Try again shortly.',
};

export function problemText(problem: ConnectionProblem): string {
  return problemMessages[problem.code ?? ''] ?? problemMessages.CONNECTION_UNAVAILABLE;
}

export const connectedNotice = {
  kind: 'success',
  text: 'Facebook is connected. WAOOAW stores the access privately.',
} as const;

const errorNotices: Record<string, { kind: 'error'; text: string }> = {
  denied: { kind: 'error', text: 'Facebook was not connected because the request was cancelled or declined.' },
  invalid_request: { kind: 'error', text: 'The Facebook response was not valid. Nothing was connected. Try again.' },
  state_invalid: {
    kind: 'error',
    text: 'That connection attempt expired or was already used. Nothing was connected. Start again.',
  },
  signin_required: { kind: 'error', text: 'Sign in again, then connect Facebook.' },
  unavailable: {
    kind: 'error',
    text: 'Connections are temporarily unavailable. Nothing was connected. Try again shortly.',
  },
  failed: { kind: 'error', text: 'Facebook could not be connected. Nothing was connected. Try again.' },
};

export function noticeFromParams(params: Record<string, string | string[] | undefined>) {
  const pick = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value);
  if (pick(params.connected) === 'meta') return connectedNotice;
  const error = pick(params.error);
  return error !== undefined && Object.hasOwn(errorNotices, error) ? errorNotices[error] : null;
}

export function formatWhen(value: string | null | undefined): string {
  if (!value) return 'Not available';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown' : `${date.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
}
