// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R007
// Constitutional basis: C-001, C-042, C-049, C-059, C-063

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { alertHref, type InboxAlert } from '@/lib/alert-controls-client';
import { AlertInbox, categoryRows } from './AlertInbox';

const alert = (overrides: Partial<InboxAlert> = {}): InboxAlert => ({
  alertId: '11111111-1111-4111-8111-111111111111',
  version: 'alert-1',
  alertClass: 'AT_RISK',
  category: 'PACE_BELOW_TARGET',
  severity: 'MEDIUM',
  source: 'AGENT_DECLARED',
  relationshipId: '22222222-2222-4222-8222-222222222222',
  occurredAt: '2026-11-25T10:00:00Z',
  dueMeaning: 'Your posts are behind pace.',
  readState: 'UNREAD',
  snoozedUntil: null,
  mutable: true,
  destination: { surface: 'RELATIONSHIP', relationshipId: '22222222-2222-4222-8222-222222222222' },
  availableAction: 'ACKNOWLEDGE',
  ...overrides,
});

type Handler = (url: string, init?: RequestInit) => { status: number; body: unknown };

function install(handler: Handler) {
  const calls: Array<{ url: string; method: string; body: unknown }> = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : null });
    const { status, body } = handler(url, init);
    return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
  }) as jest.Mock;
  return calls;
}

const inbox = (items: InboxAlert[]) => ({ schemaVersion: '1.0.0', policyVersion: '1.0', items });

describe('AlertInbox', () => {
  it('lists one inbox across agents and filters to one agent', async () => {
    const calls = install((url) =>
      url.includes('/categories')
        ? { status: 200, body: { floorCategories: ['EMERGENCY_STOP'], items: [] } }
        : { status: 200, body: inbox([alert()]) }
    );
    render(
      <AlertInbox
        agents={[
          { id: '22222222-2222-4222-8222-222222222222', name: 'Marketing agent' },
          { id: '33333333-3333-4333-8333-333333333333', name: 'Teaching agent' },
        ]}
      />
    );
    expect(await screen.findByText('Your posts are behind pace.')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Show alerts for'), {
      target: { value: '33333333-3333-4333-8333-333333333333' },
    });
    await waitFor(() =>
      expect(
        calls.some((call) => call.url.endsWith('alerts?relationshipId=33333333-3333-4333-8333-333333333333'))
      ).toBe(true)
    );
  });

  it('opens the surface the alert is about', () => {
    expect(alertHref(alert({ alertClass: 'ACTION_REQUIRED' }))).toBe(
      '/relationships/22222222-2222-4222-8222-222222222222?surface=decisions'
    );
    expect(alertHref(alert())).toBe('/relationships/22222222-2222-4222-8222-222222222222?surface=overview');
    expect(alertHref(alert({ relationshipId: null, destination: { surface: 'BILLING' } }))).toBe('/billing');
    expect(alertHref(alert({ relationshipId: null, destination: { surface: 'UNKNOWN' } }))).toBe('/home');
  });

  it('snoozes a routine alert for a day and reloads', async () => {
    const calls = install((_url, init) =>
      init?.method === 'POST' ? { status: 200, body: alert() } : { status: 200, body: inbox([alert()]) }
    );
    render(<AlertInbox />);
    fireEvent.click(await screen.findByRole('button', { name: 'Snooze for a day' }));
    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    const post = calls.find((call) => call.method === 'POST');
    expect(post?.url).toContain('/snooze');
    expect(post?.body).toMatchObject({ schemaVersion: '1.0.0', expectedAlertVersion: 'alert-1' });
  });

  it('offers no snooze for a floor alert and says so when the server refuses one', async () => {
    install((_url, init) =>
      init?.method === 'POST'
        ? { status: 409, body: { code: 'ALERT_CLASS_NOT_MUTABLE' } }
        : { status: 200, body: inbox([alert({ alertClass: 'FLOOR', category: 'EMERGENCY_STOP', mutable: false })]) }
    );
    render(<AlertInbox />);
    await screen.findByText('Your posts are behind pace.');
    expect(screen.queryByRole('button', { name: 'Snooze for a day' })).not.toBeInTheDocument();
    expect(screen.getByText('Always shown')).toBeInTheDocument();
  });

  it('never offers a floor category to switch off, and refuses clearly if the server does', async () => {
    install((url, init) => {
      if (url.includes('/categories') && init?.method === 'PUT') return { status: 409, body: {} };
      if (url.includes('/categories')) return { status: 200, body: { floorCategories: ['EMERGENCY_STOP'], items: [] } };
      return {
        status: 200,
        body: inbox([
          alert(),
          alert({
            alertId: '44444444-4444-4444-8444-444444444444',
            alertClass: 'FLOOR',
            category: 'EMERGENCY_STOP',
            mutable: false,
          }),
        ]),
      };
    });
    render(<AlertInbox showControls />);
    const section = within(await screen.findByRole('region', { name: 'Messages to your phone' }));
    expect(section.getByLabelText(/pace below target/i)).toBeInTheDocument();
    expect(section.queryByLabelText(/emergency stop/i)).not.toBeInTheDocument();
    fireEvent.click(section.getByLabelText(/pace below target/i));
    expect(await screen.findByText('This kind of alert can never be switched off.')).toBeInTheDocument();
  });

  it('says it could not load rather than showing an invented list', async () => {
    install(() => ({ status: 503, body: {} }));
    render(<AlertInbox />);
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded');
  });

  it('shows a loading state, then retries only when the customer asks', async () => {
    let attempts = 0;
    install(() => {
      attempts += 1;
      return attempts === 1 ? { status: 403, body: {} } : { status: 200, body: inbox([alert()]) };
    });
    render(<AlertInbox />);
    expect(screen.getByText('Loading your alerts…')).toBeInTheDocument();
    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('Please try again');
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(attempts).toBe(1);

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('Your posts are behind pace.')).toBeInTheDocument();
    expect(attempts).toBe(2);
  });

  it('builds the mute list from routine alerts plus existing mutes and never from floor categories', () => {
    expect(
      categoryRows([alert(), alert({ category: 'EMERGENCY_STOP', mutable: false })], {
        floorCategories: ['EMERGENCY_STOP'],
        items: [{ category: 'BUDGET', muted: true }],
      })
    ).toEqual([
      { category: 'BUDGET', muted: true },
      { category: 'PACE_BELOW_TARGET', muted: false },
    ]);
  });
});
