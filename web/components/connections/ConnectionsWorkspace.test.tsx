// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R009, WC149-R010
// Constitutional basis: C-026, C-059, C-063

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { fakeResponse } from '@/lib/pricing-admin-test-data';
import { noticeFromParams, type ProviderConnection } from '@/lib/provider-connections-client';
import { ConnectionsWorkspace } from './ConnectionsWorkspace';
import { navigateTo } from './navigate';

jest.mock('./navigate', () => ({
  ...jest.requireActual('./navigate'),
  navigateTo: jest.fn(),
}));

const connected: ProviderConnection = {
  id: '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11',
  provider: 'meta',
  status: 'CONNECTED',
  accountName: 'Acme Bakery',
  accountId: '123',
  scopes: ['pages_manage_posts'],
  expiresAt: '2027-03-01T00:00:00Z',
  connectedAt: '2027-01-01T10:00:00Z',
};
const originalFetch = global.fetch;

type Route = (body: Record<string, unknown>) => Response;

function serve(routes: Record<string, Route | Response>) {
  const fetchMock = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${String(input).replace('/api/provider-connections', '')}`;
    const route = routes[key];
    if (!route) return fakeResponse(404, { code: 'CONNECTION_NOT_FOUND' });
    return typeof route === 'function' ? route(init?.body ? JSON.parse(String(init.body)) : {}) : route;
  });
  global.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
});

test('shows a loading state, then the empty state with a Connect Facebook action and the privacy promise', async () => {
  serve({ 'GET ': fakeResponse(200, []) });
  render(<ConnectionsWorkspace />);

  expect(screen.getByText('Loading your connections...')).toBeInTheDocument();
  await screen.findByText(/You have not connected any accounts yet/);
  expect(screen.getByRole('button', { name: /Connect Facebook/ })).toBeEnabled();
  expect(screen.getByText(/The agent never sees it/)).toBeInTheDocument();
});

test('shows an error with a retry when the list cannot be loaded', async () => {
  serve({ 'GET ': fakeResponse(503, { code: 'CONNECTION_UNAVAILABLE' }) });
  render(<ConnectionsWorkspace />);

  expect(await screen.findByRole('alert')).toHaveTextContent(/could not be loaded/);
  expect(screen.queryByRole('link', { name: /Sign in again|Browse the marketplace/ })).not.toBeInTheDocument();
  serve({ 'GET ': fakeResponse(200, [connected]) });
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
  expect(await screen.findByRole('heading', { name: /Acme Bakery/ })).toBeInTheDocument();
});

test('an expired sign-in says so and offers to sign in again, returning to Connections', async () => {
  serve({ 'GET ': fakeResponse(401, { code: 'CONNECTION_SIGN_IN_REQUIRED' }) });
  render(<ConnectionsWorkspace />);

  expect(await screen.findByRole('alert')).toHaveTextContent(/Your sign-in has expired/);
  expect(screen.getByRole('alert')).not.toHaveTextContent(/not permitted/);
  expect(screen.getByRole('link', { name: 'Sign in again' })).toHaveAttribute('href', '/login?returnTo=%2Fconnections');
  expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled();
});

test('a person without a customer account is told what to do first, not that they lack permission', async () => {
  serve({ 'GET ': fakeResponse(403, { code: 'CONNECTION_ACCOUNT_REQUIRED' }) });
  render(<ConnectionsWorkspace />);

  expect(await screen.findByRole('alert')).toHaveTextContent(/Start a trial or hire an agent first/);
  expect(screen.getByRole('alert')).not.toHaveTextContent(/not permitted/);
  expect(screen.getByRole('link', { name: 'Browse the marketplace' })).toHaveAttribute('href', '/marketplace');
  expect(screen.queryByRole('button', { name: /Connect Facebook/ })).not.toBeInTheDocument();
});

test('a staff sign-in is told staff accounts own no connections, with no trial or marketplace step', async () => {
  serve({ 'GET ': fakeResponse(403, { code: 'CONNECTION_ACCOUNT_REQUIRED' }) });
  render(<ConnectionsWorkspace staff />);

  expect(await screen.findByRole('alert')).toHaveTextContent(/signed in with a staff account/);
  expect(screen.getByRole('alert')).not.toHaveTextContent(/Start a trial or hire/);
  expect(screen.queryByRole('link', { name: 'Browse the marketplace' })).not.toBeInTheDocument();
});

test('a real permission refusal on a connection keeps the permission wording', async () => {
  serve({ 'GET ': fakeResponse(403, { code: 'CONNECTION_FORBIDDEN' }) });
  render(<ConnectionsWorkspace />);

  expect(await screen.findByRole('alert')).toHaveTextContent(/not permitted to manage this connection/);
});

test('Connect Facebook starts the connection and sends the browser to the authorization address', async () => {
  const fetchMock = serve({
    'GET ': fakeResponse(200, []),
    'POST /meta/start': fakeResponse(200, {
      authorizationUrl: 'https://www.facebook.com/dialog/oauth?x=1',
      expiresAt: 'z',
    }),
  });
  render(<ConnectionsWorkspace />);

  fireEvent.click(await screen.findByRole('button', { name: /Connect Facebook/ }));

  await waitFor(() => expect(navigateTo).toHaveBeenCalledWith('https://www.facebook.com/dialog/oauth?x=1'));
  expect(fetchMock).toHaveBeenCalledWith(
    '/api/provider-connections/meta/start',
    expect.objectContaining({ method: 'POST' })
  );
});

test('refuses to navigate to an authorization address that is not https', async () => {
  serve({
    'GET ': fakeResponse(200, []),
    'POST /meta/start': fakeResponse(200, { authorizationUrl: 'javascript:alert(1)', expiresAt: 'z' }),
  });
  render(<ConnectionsWorkspace />);

  fireEvent.click(await screen.findByRole('button', { name: /Connect Facebook/ }));

  expect(await screen.findByText(/Facebook could not be opened/)).toBeInTheDocument();
  expect(navigateTo).not.toHaveBeenCalled();
});

test('a connected account shows its status, explanation and the approval-gated publish form', async () => {
  const published = jest.fn((body: Record<string, unknown>) => {
    void body;
    return fakeResponse(200, { providerPostId: 'fb-post-99', publishedAt: '2027-01-02T00:00:00Z' });
  });
  serve({ 'GET ': fakeResponse(200, [connected]), [`POST /${connected.id}/publish`]: published });
  render(<ConnectionsWorkspace />);

  expect(await screen.findByText('Connected')).toBeInTheDocument();
  expect(screen.getByText(/only the exact posts you approve/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /Connect Facebook/ })).not.toBeInTheDocument();
  const submit = screen.getByRole('button', { name: 'Publish post' });
  const message = screen.getByLabelText('Post message');
  const approval = screen.getByLabelText('I approve this exact post to be published to my Facebook Page');

  fireEvent.change(message, { target: { value: 'Fresh bread today' } });
  expect(screen.getByText('17 / 2000')).toBeInTheDocument();
  expect(message).toHaveAttribute('maxlength', '2000');
  expect(submit).toBeDisabled();
  fireEvent.click(approval);
  expect(submit).toBeEnabled();
  fireEvent.change(message, { target: { value: 'Fresh bread today!' } });
  expect(approval).not.toBeChecked();
  expect(submit).toBeDisabled();
  fireEvent.click(approval);
  fireEvent.click(submit);

  await screen.findByText(/fb-post-99/);
  expect(published).toHaveBeenCalledWith({
    message: 'Fresh bread today!',
    approved: true,
    approvalNote: expect.any(String),
  });
  expect(message).toHaveValue('');
});

test('a publish that needs repair shows a Reconnect prompt', async () => {
  serve({
    'GET ': fakeResponse(200, [connected]),
    [`POST /${connected.id}/publish`]: fakeResponse(409, { code: 'CONNECTION_NEEDS_REPAIR' }),
    'POST /meta/start': fakeResponse(200, { authorizationUrl: 'https://www.facebook.com/dialog', expiresAt: 'z' }),
  });
  render(<ConnectionsWorkspace />);
  fireEvent.change(await screen.findByLabelText('Post message'), { target: { value: 'Hello' } });
  fireEvent.click(screen.getByLabelText(/I approve this exact post/));
  fireEvent.click(screen.getByRole('button', { name: 'Publish post' }));

  const reconnect = await screen.findByRole('button', { name: 'Reconnect Facebook' });
  expect(screen.getByText(/Reconnect needed/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Publish post' })).not.toBeInTheDocument();
  fireEvent.click(reconnect);
  await waitFor(() => expect(navigateTo).toHaveBeenCalledWith('https://www.facebook.com/dialog'));
});

test('a connection that needs repair offers Reconnect and no publish form; a revoked one offers neither', async () => {
  serve({
    'GET ': fakeResponse(200, [
      { ...connected, status: 'NEEDS_REPAIR' },
      { ...connected, id: 'b2b2b2b2-6a16-4d35-9b44-7f3a1f0d1a11', status: 'REVOKED', accountName: 'Old Page' },
    ]),
  });
  render(<ConnectionsWorkspace />);

  expect(await screen.findByText('Needs repair')).toBeInTheDocument();
  expect(screen.getByText('Revoked')).toBeInTheDocument();
  expect(screen.getAllByRole('button', { name: 'Reconnect Facebook' })).toHaveLength(1);
  expect(screen.queryByLabelText('Post message')).not.toBeInTheDocument();
  expect(screen.getAllByRole('button', { name: /^Revoke/ })).toHaveLength(1);
  expect(screen.queryByRole('button', { name: /Connect Facebook/ })).not.toBeInTheDocument();
});

test('Revoke asks for confirmation in a dialog, restores focus on Escape, and revokes on confirm', async () => {
  const fetchMock = serve({
    'GET ': fakeResponse(200, [connected]),
    [`POST /${connected.id}/revoke`]: fakeResponse(204, undefined),
  });
  render(<ConnectionsWorkspace />);
  const revoke = await screen.findByRole('button', { name: /^Revoke/ });

  fireEvent.click(revoke);
  const dialog = screen.getByRole('dialog');
  expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus();
  fireEvent.keyDown(dialog, { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(revoke).toHaveFocus();
  expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining('/revoke'), expect.anything());

  serve({
    'GET ': fakeResponse(200, []),
    [`POST /${connected.id}/revoke`]: fakeResponse(204, undefined),
  });
  fireEvent.click(revoke);
  fireEvent.click(screen.getByRole('button', { name: 'Confirm revoke' }));

  expect(await screen.findByText(/Connection revoked/)).toBeInTheDocument();
  await screen.findByText(/You have not connected any accounts yet/);
});

test('a failed revoke keeps the dialog open with an error', async () => {
  serve({
    'GET ': fakeResponse(200, [connected]),
    [`POST /${connected.id}/revoke`]: fakeResponse(503, { code: 'CONNECTION_UNAVAILABLE' }),
  });
  render(<ConnectionsWorkspace />);
  fireEvent.click(await screen.findByRole('button', { name: /^Revoke/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Confirm revoke' }));

  expect(await within(screen.getByRole('dialog')).findByRole('alert')).toHaveTextContent(/temporarily unavailable/);
});

test('the return notice is shown, and only fixed codes are ever turned into text', async () => {
  serve({ 'GET ': fakeResponse(200, []) });
  render(<ConnectionsWorkspace initialNotice={noticeFromParams({ connected: 'meta' })} />);

  expect(await screen.findByRole('status')).toHaveTextContent(/Facebook is connected/);
  expect(noticeFromParams({ error: 'denied' })?.kind).toBe('error');
  expect(noticeFromParams({ error: ['state_invalid'] })?.text).toMatch(/expired or was already used/);
  expect(noticeFromParams({ error: '<script>alert(1)</script>' })).toBeNull();
  expect(noticeFromParams({ error: 'constructor' })).toBeNull();
  expect(noticeFromParams({ connected: 'other' })).toBeNull();
});
