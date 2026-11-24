// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R009, WC149-R010; work-contracts/WC-167-acceptance-demo-readiness.md WC167-R002
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
  CONNECTION_SIGN_IN_REQUIRED: 'Your sign-in has expired. Sign in again to see and manage your connections.',
  CONNECTION_ACCOUNT_REQUIRED:
    'We could not confirm a customer account for this action. Start a trial or hire an agent first, then come back here. If you already have, sign in again.',
  CONNECTION_INVALID: 'The request was not valid. Check the post text and try again. Nothing was published.',
  CONNECTION_RATE_LIMITED: 'Too many requests in a minute. Wait and try again.',
  CONNECTION_UNAVAILABLE: 'Connections are temporarily unavailable. Nothing was changed. Try again shortly.',
};

export function problemText(problem: ConnectionProblem, staff = false): string {
  if (staff && problem.code === 'CONNECTION_ACCOUNT_REQUIRED') return staffAccountText;
  return problemMessages[problem.code ?? ''] ?? problemMessages.CONNECTION_UNAVAILABLE;
}

// A staff sign-in has no customer account, so telling it to start a trial would send it the wrong way.
const staffAccountText =
  'You are signed in with a staff account. Staff accounts do not own connections; customers connect their own accounts from a customer sign-in.';

export type ProblemAction = { href: string; label: string };

// A refusal that the person can fix gets the one next step that fixes it; anything else offers none.
export function problemAction(problem: ConnectionProblem, staff = false): ProblemAction | null {
  if (problem.code === 'CONNECTION_SIGN_IN_REQUIRED') {
    return { href: `/login?returnTo=${encodeURIComponent('/connections')}`, label: 'Sign in again' };
  }
  if (problem.code === 'CONNECTION_ACCOUNT_REQUIRED' && !staff)
    return { href: '/marketplace', label: 'Browse the marketplace' };
  return null;
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
