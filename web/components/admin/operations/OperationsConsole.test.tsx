// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009, WC171-R010
// Constitutional basis: C-023, C-049, C-059, C-063

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { OperationsConsole } from './OperationsConsole';

jest.mock('@/components/admin/StepUpCommand', () => ({
  StepUpCommand: () => <button type="button">Confirm step-up</button>,
}));

const blocked = {
  outboxId: '11111111-1111-4111-8111-111111111111',
  relationshipId: '22222222-2222-4222-8222-222222222222',
  purpose: 'GUEST_DISCOVERY',
  templateCategory: 'UTILITY',
  blockedReason: 'PROVIDER_REJECTED',
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
  'operations/blocked-messages': { status: 200, body: { items: [blocked] } },
  'operations/pages': {
    status: 200,
    body: {
      items: [
        {
          signal: 'DEAD_LETTER_AGE_BREACH',
          outcome: 'EMITTED',
          reason: 'HANDED_TO_MONITORING',
          recordedAt: '2026-11-25T10:30:00Z',
        },
      ],
    },
  },
};

describe('OperationsConsole', () => {
  it('shows the overview, the blocked message without recipient or body, and the honest page outcome', async () => {
    install(baseRoutes);
    render(<OperationsConsole canResolve />);

    expect(await screen.findByText('GUEST DISCOVERY'.toLowerCase(), { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/blocked for 42 min/)).toBeInTheDocument();
    expect(screen.getByText(/operator page: emitted — 7/)).toBeInTheDocument();
    expect(screen.getByText(/identity-schema: healthy/)).toBeInTheDocument();
    expect(screen.getByText(/a person receiving it is not proven here/)).toBeInTheDocument();
    expect(screen.queryByText(/\+91|whatsapp:/i)).not.toBeInTheDocument();
  });

  it('resolves a blocked message with a reason and an idempotency key, then reloads', async () => {
    const calls = install({
      ...baseRoutes,
      [`blocked-messages/${blocked.outboxId}/resolve`]: { status: 201, body: { resolutionId: 'r-1', replayed: false } },
    });
    render(<OperationsConsole canResolve />);
    const reason = await screen.findByLabelText('Reason');
    fireEvent.change(reason, { target: { value: 'Meta error 131026, recipient not on WhatsApp' } });
    fireEvent.click(screen.getByRole('button', { name: 'Close with a reason' }));

    expect(await screen.findByText(/The message was kept/)).toBeInTheDocument();
    const post = calls.find((call) => call.method === 'POST');
    expect(post?.body).toEqual({
      schemaVersion: '1.0.0',
      action: 'CLOSE_WITH_REASON',
      reason: 'Meta error 131026, recipient not on WhatsApp',
    });
    expect(post?.key).toMatch(/[0-9a-f-]{36}/);
  });

  it('asks for a reason before it calls anything', async () => {
    const calls = install(baseRoutes);
    render(<OperationsConsole canResolve />);
    fireEvent.click(await screen.findByRole('button', { name: 'Mark undeliverable' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('reason of at least five characters');
    expect(calls.some((call) => call.method === 'POST')).toBe(false);
  });

  it('offers the multi-factor step when the server asks for it and changes nothing', async () => {
    install({
      ...baseRoutes,
      [`blocked-messages/${blocked.outboxId}/resolve`]: { status: 403, body: { code: 'OPERATIONS_STEP_UP_REQUIRED' } },
    });
    render(<OperationsConsole canResolve />);
    fireEvent.change(await screen.findByLabelText('Reason'), { target: { value: 'Retry after template approval' } });
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('button', { name: 'Confirm step-up' })).toBeInTheDocument();
  });

  it('gives an administrator the read view only, with no resolve or acknowledge action', async () => {
    install(baseRoutes);
    render(<OperationsConsole canResolve={false} />);
    await screen.findByText(/blocked for 42 min/);
    expect(screen.queryByLabelText('Reason')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Close with a reason' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Acknowledge' })).not.toBeInTheDocument();
  });

  it('acknowledges a page for the Founder', async () => {
    const calls = install({
      ...baseRoutes,
      'pages/DEAD_LETTER_AGE_BREACH/acknowledge': { status: 202, body: { code: 'DEAD_LETTER_AGE_BREACH' } },
    });
    render(<OperationsConsole canResolve />);
    fireEvent.click(await screen.findByRole('button', { name: 'Acknowledge' }));
    await waitFor(() => expect(calls.some((call) => call.url.includes('/acknowledge'))).toBe(true));
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

  it('reads the work timeline and says the spend chain cannot be read yet', async () => {
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
    const section = within(await screen.findByRole('region', { name: 'Work and spend' }));
    fireEvent.change(section.getByLabelText('Tenant'), { target: { value: '11111111-1111-4111-8111-111111111111' } });
    fireEvent.change(section.getByLabelText('Relationship'), {
      target: { value: '22222222-2222-4222-8222-222222222222' },
    });
    fireEvent.click(section.getByRole('button', { name: 'Read' }));
    expect(await section.findByText(/The post was published/)).toBeInTheDocument();
    expect(section.getByText(/needs a route grant to the billing engine/)).toBeInTheDocument();
  });

  it('refuses a lookup that is not two full identifiers', async () => {
    install(baseRoutes);
    render(<OperationsConsole canResolve />);
    const section = within(await screen.findByRole('region', { name: 'Work and spend' }));
    fireEvent.click(section.getByRole('button', { name: 'Read' }));
    expect(await section.findByRole('alert')).toHaveTextContent('full identifiers');
  });
});
