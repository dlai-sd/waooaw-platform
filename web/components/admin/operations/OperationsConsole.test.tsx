// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009, WC171-R010
// Constitutional basis: C-023, C-049, C-059, C-063

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { savePendingStepUp } from '@/lib/step-up-resume';
import { OperationsConsole } from './OperationsConsole';

jest.mock('@/components/admin/StepUpCommand', () => ({
  StepUpCommand: ({ pendingKey, payload }: { pendingKey?: string; payload?: unknown }) => (
    <button data-key={pendingKey} data-payload={JSON.stringify(payload)} type="button">
      Confirm step-up
    </button>
  ),
}));

const blocked = {
  outboxId: '11111111-1111-4111-8111-111111111111',
  relationshipId: '22222222-2222-4222-8222-222222222222',
  purpose: 'GUEST_DISCOVERY',
  templateCategory: 'UTILITY',
  blockedReason: 'PROVIDER_REJECTED',
  reasonText: 'WhatsApp refused the message.',
  canUnblock: true,
  attemptNumber: 3,
  blockedSince: '2026-11-25T10:00:00Z',
  ageMinutes: 42,
};

const overview = {
  environment: 'demo',
  whatsApp: 'ACTIVE',
  openSignals: 1,
  blockedMessages: 1,
  unresolvedMessages: 0,
  oldestQueuedMinutes: null,
  oldestBlockedMinutes: 42,
  deliveries: [{ channel: 'operator_page', outcome: 'EMITTED', count: 7 }],
  services: [{ name: 'identity-schema', state: 'HEALTHY' }],
  observedAt: '2026-11-25T11:00:00Z',
};

const customer = {
  registrationId: '33333333-3333-4333-8333-333333333333',
  displayName: 'Asha Rao',
  maskedEmail: 'a***@example.com',
  maskedMobile: null,
  status: 'LOGGED_IN_ONLY',
  registrationState: 'Started',
  firstSeenAt: '2026-11-25T09:00:00Z',
  lastActiveAt: '2026-11-25T10:00:00Z',
  registeredAt: null,
};

type Reply = { status: number; body: unknown };

function install(routes: Record<string, Reply | ((init?: RequestInit) => Reply)>) {
  const calls: Array<{ url: string; method: string; body: unknown; key?: string }> = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const headers = (init?.headers ?? {}) as Record<string, string>;
    calls.push({
      url,
      method: init?.method ?? 'GET',
      body: init?.body ? JSON.parse(String(init.body)) : null,
      key: headers['Idempotency-Key'],
    });
    const match = Object.keys(routes)
      .filter((path) => url.includes(path))
      .sort((left, right) => right.length - left.length)[0];
    const reply = match ? routes[match] : { status: 404, body: {} };
    const { status, body } = typeof reply === 'function' ? reply(init) : reply;
    return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
  }) as jest.Mock;
  return calls;
}

const baseRoutes = {
  'operations/overview': { status: 200, body: overview },
  'operations/blocked-messages/history': {
    status: 200,
    body: {
      items: [
        {
          resolutionId: 'r-0',
          outboxId: blocked.outboxId,
          action: 'RETRY',
          reason: 'Template approved now',
          resolvedBy: 'founder-subject',
          resolvedAt: '2026-11-25T10:45:00Z',
        },
      ],
    },
  },
  'operations/blocked-messages': { status: 200, body: { items: [blocked] } },
  'operations/pages': {
    status: 200,
    body: {
      items: [
        {
          signal: 'DEAD_LETTER_AGE_BREACH',
          outcome: 'EMITTED',
          reason: 'HANDED_TO_MONITORING',
          count: 3,
          firstRecordedAt: '2026-11-25T08:30:00Z',
          recordedAt: '2026-11-25T10:30:00Z',
        },
      ],
    },
  },
  'operations/customers': { status: 200, body: { items: [customer], nextCursor: null } },
};

const openTab = (name: string | RegExp) => fireEvent.click(screen.getByRole('tab', { name }));

describe('OperationsConsole', () => {
  beforeEach(() => window.sessionStorage.clear());

  it('opens on the overview and shows one section at a time in tabs', async () => {
    install(baseRoutes);
    render(<OperationsConsole canResolve />);

    expect(await screen.findByText(/operator page: emitted — 7/)).toBeInTheDocument();
    expect(screen.getByText(/identity-schema: healthy/)).toBeInTheDocument();
    expect(screen.queryByText(/blocked for 42 min/)).not.toBeInTheDocument();
    await screen.findByRole('tab', { name: 'Blocked messages (1)' });
    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual([
      'Overview',
      'Blocked messages (1)',
      'Urgent alerts',
      'Customers',
      'Work and spend',
    ]);
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');
  });

  it('shows the blocked message with a plain reason and no recipient or body', async () => {
    install(baseRoutes);
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    await screen.findByRole('tab', { name: 'Blocked messages (1)' });
    openTab(/Blocked messages/);

    expect(screen.getByText(/blocked for 42 min/)).toBeInTheDocument();
    expect(screen.getByText('Why: WhatsApp refused the message.')).toBeInTheDocument();
    expect(screen.getByText(/Retry queued · .* by founder-subject — “Template approved now”/)).toBeInTheDocument();
    expect(screen.queryByText(/\+91|whatsapp:/i)).not.toBeInTheDocument();
  });

  it('queues a retry with a reason and a key, says delivery is not yet confirmed, then reloads', async () => {
    const calls = install({
      ...baseRoutes,
      [`blocked-messages/${blocked.outboxId}/resolve`]: { status: 201, body: { resolutionId: 'r-1', replayed: false } },
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    await screen.findByRole('tab', { name: 'Blocked messages (1)' });
    openTab(/Blocked messages/);
    fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Template approved by Meta today' } });
    fireEvent.click(screen.getByRole('button', { name: 'Retry send' }));

    expect(
      await screen.findByText(
        'Queued for retry. Delivery is confirmed when the message leaves this list — refresh to check.'
      )
    ).toBeInTheDocument();
    const post = calls.find((call) => call.method === 'POST');
    expect(post?.body).toEqual({
      schemaVersion: '1.0.0',
      action: 'RETRY',
      reason: 'Template approved by Meta today',
    });
    expect(post?.key).toMatch(/[0-9a-f-]{36}/);
  });

  it('closes a message with a reason', async () => {
    const calls = install({
      ...baseRoutes,
      [`blocked-messages/${blocked.outboxId}/resolve`]: { status: 201, body: { resolutionId: 'r-2', replayed: false } },
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    await screen.findByRole('tab', { name: 'Blocked messages (1)' });
    openTab(/Blocked messages/);
    fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Recipient is not on WhatsApp' } });
    fireEvent.click(screen.getByRole('button', { name: 'Close with a reason' }));

    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    expect(calls.find((call) => call.method === 'POST')?.body).toMatchObject({ action: 'CLOSE_WITH_REASON' });
  });

  it('asks for a reason before it calls anything', async () => {
    const calls = install(baseRoutes);
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    await screen.findByRole('tab', { name: 'Blocked messages (1)' });
    openTab(/Blocked messages/);
    fireEvent.click(screen.getByRole('button', { name: 'Mark undeliverable' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('reason of at least five characters');
    expect(calls.some((call) => call.method === 'POST')).toBe(false);
  });

  it('offers no Retry send for a message that cannot be sent again', async () => {
    install({
      ...baseRoutes,
      'operations/blocked-messages': {
        status: 200,
        body: { items: [{ ...blocked, canUnblock: false, reasonText: 'The agent relationship has ended.' }] },
      },
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    await screen.findByRole('tab', { name: 'Blocked messages (1)' });
    openTab(/Blocked messages/);

    expect(screen.queryByRole('button', { name: 'Retry send' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Close with a reason' })).toBeInTheDocument();
    expect(screen.getByText(/cannot be sent again/)).toBeInTheDocument();
  });

  it('offers the multi-factor step when the server asks for it and changes nothing', async () => {
    install({
      ...baseRoutes,
      [`blocked-messages/${blocked.outboxId}/resolve`]: { status: 403, body: { code: 'OPERATIONS_STEP_UP_REQUIRED' } },
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    await screen.findByRole('tab', { name: 'Blocked messages (1)' });
    openTab(/Blocked messages/);
    fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Retry after template approval' } });
    fireEvent.click(screen.getByRole('button', { name: 'Retry send' }));
    const step = await screen.findByRole('button', { name: 'Confirm step-up' });
    expect(step).toHaveAttribute('data-key', 'operations.resolve');
    expect(JSON.parse(step.getAttribute('data-payload') ?? '{}')).toEqual({
      outboxId: blocked.outboxId,
      action: 'RETRY',
      reason: 'Retry after template approval',
    });
    expect(screen.getByText(/needs a fresh multi-factor sign-in/)).toBeInTheDocument();
  });

  it('resumes the interrupted retry once after the step-up and says so', async () => {
    savePendingStepUp('operations.resolve', {
      outboxId: blocked.outboxId,
      action: 'RETRY',
      reason: 'Retry after template approval',
    });
    const calls = install({
      ...baseRoutes,
      [`blocked-messages/${blocked.outboxId}/resolve`]: { status: 201, body: { resolutionId: 'r-9', replayed: false } },
    });
    const { unmount } = render(<OperationsConsole canResolve />);

    expect(await screen.findByText('Resuming your action after sign-in…')).toBeInTheDocument();
    expect(await screen.findByText(/Queued for retry/)).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Blocked messages/ })).toHaveAttribute('aria-selected', 'true');
    const posts = calls.filter((call) => call.method === 'POST');
    expect(posts).toHaveLength(1);
    expect(posts[0].body).toEqual({
      schemaVersion: '1.0.0',
      action: 'RETRY',
      reason: 'Retry after template approval',
    });
    unmount();

    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    expect(calls.filter((call) => call.method === 'POST')).toHaveLength(1);
  });

  it('does not resume an action that was remembered more than ten minutes ago', async () => {
    savePendingStepUp(
      'operations.resolve',
      { outboxId: blocked.outboxId, action: 'RETRY', reason: 'Retry after template approval' },
      Date.now() - 11 * 60 * 1000
    );
    const calls = install(baseRoutes);
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    expect(calls.some((call) => call.method === 'POST')).toBe(false);
  });

  it('says plainly when the retry could not be queued, or WhatsApp is not active', async () => {
    let status = 500;
    install({
      ...baseRoutes,
      [`blocked-messages/${blocked.outboxId}/resolve`]: () => ({
        status,
        body: status === 503 ? { code: 'OPERATIONS_WHATSAPP_INACTIVE' } : {},
      }),
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    await screen.findByRole('tab', { name: 'Blocked messages (1)' });
    openTab(/Blocked messages/);
    fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Retry after template approval' } });
    fireEvent.click(screen.getByRole('button', { name: 'Retry send' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be queued for retry');
    status = 503;
    fireEvent.click(screen.getByRole('button', { name: 'Retry send' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('WhatsApp is not active'));
  });

  it('shows a failed read as an error with Retry instead of an empty list, and retries it', async () => {
    let healthy = false;
    install({
      ...baseRoutes,
      'operations/blocked-messages': () =>
        healthy ? { status: 200, body: { items: [blocked] } } : { status: 500, body: {} },
      'operations/blocked-messages/history': { status: 500, body: {} },
      'operations/pages': { status: 500, body: {} },
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    openTab(/Blocked messages/);
    expect(
      await screen.findByText('Blocked messages could not be loaded right now. Nothing was changed.')
    ).toBeInTheDocument();
    expect(screen.getByText('Recent changes could not be loaded right now. Nothing was changed.')).toBeInTheDocument();
    expect(screen.queryByText('No blocked messages.')).not.toBeInTheDocument();
    expect(screen.queryByText('No blocked message has been changed yet.')).not.toBeInTheDocument();

    healthy = true;
    fireEvent.click(screen.getAllByRole('button', { name: 'Retry' })[0]);
    expect(await screen.findByText(/blocked for 42 min/)).toBeInTheDocument();

    openTab('Urgent alerts');
    expect(
      await screen.findByText('Urgent alerts could not be loaded right now. Nothing was changed.')
    ).toBeInTheDocument();
    expect(screen.queryByText('No urgent alerts recorded.')).not.toBeInTheDocument();
  });

  it('shows Loading while a read is in flight, and an empty state only for a confirmed empty answer', async () => {
    install({
      ...baseRoutes,
      'operations/blocked-messages': { status: 200, body: { items: [] } },
    });
    render(<OperationsConsole canResolve />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
    await screen.findByText(/operator page: emitted/);
    openTab(/Blocked messages/);
    expect(await screen.findByText('No blocked messages.')).toBeInTheDocument();
  });

  it('shows a failed overview as an error with Retry, not as a blank page', async () => {
    install({ ...baseRoutes, 'operations/overview': { status: 500, body: {} } });
    render(<OperationsConsole canResolve />);
    expect(
      await screen.findByText('The overview could not be loaded right now. Nothing was changed.')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('moves between tabs with the arrow, Home and End keys and keeps one tab in the tab order', async () => {
    install(baseRoutes);
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    const tabs = () => screen.getAllByRole('tab');

    expect(tabs().map((tab) => tab.getAttribute('tabindex'))).toEqual(['0', '-1', '-1', '-1', '-1']);
    fireEvent.keyDown(tabs()[0], { key: 'ArrowRight' });
    expect(tabs()[1]).toHaveAttribute('aria-selected', 'true');
    expect(tabs()[1]).toHaveFocus();
    expect(tabs().map((tab) => tab.getAttribute('tabindex'))).toEqual(['-1', '0', '-1', '-1', '-1']);
    fireEvent.keyDown(tabs()[1], { key: 'ArrowLeft' });
    fireEvent.keyDown(tabs()[0], { key: 'ArrowLeft' });
    expect(tabs()[4]).toHaveAttribute('aria-selected', 'true');
    expect(tabs()[4]).toHaveFocus();
    fireEvent.keyDown(tabs()[4], { key: 'ArrowRight' });
    expect(tabs()[0]).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(tabs()[0], { key: 'End' });
    expect(tabs()[4]).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(tabs()[4], { key: 'Home' });
    expect(tabs()[0]).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(tabs()[0], { key: 'x' });
    expect(tabs()[0]).toHaveAttribute('aria-selected', 'true');
  });

  it('gives an administrator the read view only, with no retry, acknowledge or customers tab', async () => {
    install(baseRoutes);
    render(<OperationsConsole canResolve={false} />);
    await screen.findByText(/operator page: emitted/);
    expect(screen.queryByRole('tab', { name: 'Customers' })).not.toBeInTheDocument();
    await screen.findByRole('tab', { name: 'Blocked messages (1)' });
    openTab(/Blocked messages/);
    expect(screen.queryByLabelText('Reason')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Retry send' })).not.toBeInTheDocument();
    openTab('Urgent alerts');
    expect(screen.queryByRole('button', { name: 'Acknowledge' })).not.toBeInTheDocument();
  });

  it('groups a standing alert into one line with a count and acknowledges it for the Founder', async () => {
    const calls = install({
      ...baseRoutes,
      'pages/DEAD_LETTER_AGE_BREACH/acknowledge': { status: 202, body: { code: 'DEAD_LETTER_AGE_BREACH' } },
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    openTab('Urgent alerts');

    expect(await screen.findByText(/dead letter age breach: emitted · 3 times, first/)).toBeInTheDocument();
    expect(screen.getByText(/a person receiving it is not proven here/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Acknowledge' }));
    await waitFor(() => expect(calls.some((call) => call.url.includes('/acknowledge'))).toBe(true));
  });

  it('shows the approved WhatsApp limits, what is used, and whether registration codes are on', async () => {
    install({
      ...baseRoutes,
      'operations/overview': {
        status: 200,
        body: {
          ...overview,
          limits: {
            windowStartsAt: '2026-11-26T18:10:00Z',
            windowExpiresAt: '2026-12-03T18:10:00Z',
            maximumMessages: 200,
            maximumMessagesPerMinute: 6,
            maximumSpendInr: 500,
            maximumCostPerMessageInr: 5,
            guestAdmission: true,
            registrationCodes: true,
            messagesReserved: 12,
            spendReservedInr: 60,
          },
        },
      },
    });
    render(<OperationsConsole canResolve />);

    expect(await screen.findByRole('heading', { name: 'WhatsApp limits you approved' })).toBeInTheDocument();
    expect(screen.getByText('12 of 200 used')).toBeInTheDocument();
    expect(screen.getByText('Up to 6 a minute')).toBeInTheDocument();
    expect(screen.getByText(/₹60\.00 of ₹500\.00 reserved, at most ₹5\.00 per message/)).toBeInTheDocument();
    expect(screen.getByText('Open to the public')).toBeInTheDocument();
    expect(screen.getByText('On')).toBeInTheDocument();
  });

  it('shows no limits block when no WhatsApp authority is configured', async () => {
    install({ ...baseRoutes, 'operations/overview': { status: 200, body: { ...overview, limits: null } } });
    render(<OperationsConsole canResolve />);

    await screen.findByText('Alert delivery, last 24 hours');
    expect(screen.queryByText('WhatsApp limits you approved')).not.toBeInTheDocument();
  });

  it('says WhatsApp is not active instead of showing an empty queue as healthy', async () => {
    install({
      ...baseRoutes,
      'operations/overview': {
        status: 200,
        body: { ...overview, whatsApp: 'INACTIVE', whatsAppReason: 'NOT_ENABLED' },
      },
      'operations/blocked-messages': { status: 503, body: { code: 'OPERATIONS_WHATSAPP_INACTIVE' } },
    });
    render(<OperationsConsole canResolve />);
    expect(await screen.findByText(/Not active \(not enabled\)/)).toBeInTheDocument();
  });

  it('reads the work timeline and describes a failed spend chain read neutrally', async () => {
    install({
      ...baseRoutes,
      'work-timeline': {
        status: 200,
        body: {
          emergencyStopActive: false,
          workItems: [
            {
              workItemId: 'w1',
              workItemType: 'SOCIAL_POST',
              state: 'COMPLETED',
              reasonCode: null,
              sentence: 'The post was published.',
            },
          ],
        },
      },
      'spend-chain': { status: 503, body: { code: 'SPEND_CHAIN_READ_UNAVAILABLE' } },
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    openTab('Work and spend');
    const section = within(await screen.findByRole('region', { name: 'Work and spend' }));
    fireEvent.change(section.getByLabelText('Tenant'), { target: { value: '11111111-1111-4111-8111-111111111111' } });
    fireEvent.change(section.getByLabelText('Relationship'), {
      target: { value: '22222222-2222-4222-8222-222222222222' },
    });
    fireEvent.click(section.getByRole('button', { name: 'Read' }));
    expect(await section.findByText(/The post was published/)).toBeInTheDocument();
    expect(
      section.getByText('The spend chain could not be read: the billing engine did not answer.')
    ).toBeInTheDocument();
    expect(section.queryByText(/route grant/)).not.toBeInTheDocument();
  });

  it('refuses a lookup that is not two full identifiers', async () => {
    install(baseRoutes);
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    openTab('Work and spend');
    const section = within(await screen.findByRole('region', { name: 'Work and spend' }));
    fireEvent.click(section.getByRole('button', { name: 'Read' }));
    expect(await section.findByRole('alert')).toHaveTextContent('full identifiers');
  });

  it('lists the latest customers with masked contact details and their status', async () => {
    install(baseRoutes);
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    openTab('Customers');

    const table = within(await screen.findByRole('table', { name: 'Customers' }));
    expect(table.getByText('Asha Rao')).toBeInTheDocument();
    expect(table.getByText('a***@example.com')).toBeInTheDocument();
    expect(table.getByText('Logged in only')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Older' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Newer' })).toBeDisabled();
  });

  it('filters customers by name, contact and status, and pages with a cursor', async () => {
    const calls = install({
      ...baseRoutes,
      'operations/customers': (init) => ({
        status: 200,
        body: { items: [customer], nextCursor: init ? null : 'cursor-2' },
      }),
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    openTab('Customers');
    await screen.findByRole('table', { name: 'Customers' });

    fireEvent.change(screen.getByLabelText('Name starts with'), { target: { value: 'Asha' } });
    fireEvent.change(screen.getByLabelText('Email or mobile number (exact)'), {
      target: { value: 'asha@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'REGISTERED' } });
    fireEvent.click(screen.getByRole('button', { name: 'Search' }));

    await waitFor(() => expect(calls.filter((call) => call.url.includes('customers')).length).toBe(2));
    const search = new URL(calls.filter((call) => call.url.includes('customers'))[1].url, 'http://localhost')
      .searchParams;
    expect(search.get('name')).toBe('Asha');
    expect(search.get('contact')).toBe('asha@example.com');
    expect(search.get('status')).toBe('REGISTERED');
    expect(search.get('pageSize')).toBe('10');
  });

  it('walks to the next page by cursor and back', async () => {
    let page = 0;
    const calls = install({
      ...baseRoutes,
      'operations/customers': () => {
        page += 1;
        return { status: 200, body: { items: [customer], nextCursor: page === 1 ? 'cursor-2' : null } };
      },
    });
    render(<OperationsConsole canResolve />);
    await screen.findByText(/operator page: emitted/);
    openTab('Customers');
    await screen.findByRole('table', { name: 'Customers' });

    fireEvent.click(screen.getByRole('button', { name: 'Older' }));
    await waitFor(() => expect(calls.filter((call) => call.url.includes('customers')).length).toBe(2));
    expect(calls.filter((call) => call.url.includes('customers'))[1].url).toContain('cursor=cursor-2');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Newer' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Newer' }));
    await waitFor(() => expect(calls.filter((call) => call.url.includes('customers')).length).toBe(3));
    expect(calls.filter((call) => call.url.includes('customers'))[2].url).not.toContain('cursor=');
  });
});
