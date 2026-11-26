// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R022, R028, R032
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { operationMessages } from '@/lib/operation-i18n';
import { AgentOperationSettings, parseOverrides, type OperationSettings } from './AgentOperationSettings';

const copy = operationMessages('en');
const initial: OperationSettings = {
  chatAllowanceDefault: 1000,
  chatAllowanceByProfessionalType: { TYPE_A: 500 },
  instagramConnectEnabled: false,
  publishSandboxOnly: true,
  sandboxAccountIds: ['page-1'],
  registryReadsEnabled: false,
};

function reply(status: number, body: unknown) {
  return { ok: status < 300, status, json: async () => body } as unknown as Response;
}

function install(routes: Record<string, () => Response>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input).replace('/api/admin/agent-operation/', '');
    calls.push({ method: init?.method ?? 'GET', path, body: init?.body ? JSON.parse(String(init.body)) : null });
    const handler = routes[`${init?.method ?? 'GET'} ${path}`];
    return handler ? handler() : reply(404, {});
  }) as jest.Mock;
  return calls;
}

describe('parseOverrides', () => {
  it('reads one kind of agent per line and refuses anything that is not a whole number from 1 to 1,000,000', () => {
    expect(parseOverrides('A=5\n\n B = 1000000 ')).toEqual({ A: 5, B: 1_000_000 });
    expect(parseOverrides('')).toEqual({});
    for (const bad of ['A', 'A=0', 'A=1.5', 'A=1000001', '=5', 'A=1=2', 'A=x']) expect(parseOverrides(bad)).toBeNull();
  });
});

describe('AgentOperationSettings', () => {
  afterEach(() => jest.restoreAllMocks());

  it('shows the Founder’s current values and the default allowance of 1,000 chats', async () => {
    install({
      'GET share': () => reply(200, { days: [], relationshipsCounted: 0, assistantShare: null }),
      'GET attention': () => reply(200, []),
    });
    render(<AgentOperationSettings copy={copy} initial={initial} />);

    expect(screen.getByLabelText(copy.allowanceDefault)).toHaveValue(1000);
    expect(screen.getByLabelText(copy.allowanceByType)).toHaveValue('TYPE_A=500');
    expect(screen.getByLabelText(copy.instagramSwitch)).not.toBeChecked();
    expect(screen.getByLabelText(copy.sandboxOnly)).toBeChecked();
    expect(screen.getByLabelText(copy.sandboxAccounts)).toHaveValue('page-1');
    expect(screen.getByLabelText(copy.registrySwitch)).not.toBeChecked();
    expect(await screen.findAllByText(copy.nothingYet)).toHaveLength(2);
  });

  it('saves the allowance and the switches as one change', async () => {
    const calls = install({
      'GET share': () => reply(200, { days: [], relationshipsCounted: 0, assistantShare: null }),
      'GET attention': () => reply(200, []),
      'PUT settings': () => reply(200, {}),
    });
    render(<AgentOperationSettings copy={copy} initial={initial} />);

    fireEvent.change(screen.getByLabelText(copy.allowanceDefault), { target: { value: '750' } });
    fireEvent.change(screen.getByLabelText(copy.allowanceByType), { target: { value: 'TYPE_A=500\nTYPE_B=200' } });
    fireEvent.click(screen.getByLabelText(copy.instagramSwitch));
    fireEvent.click(screen.getByLabelText(copy.sandboxOnly));
    fireEvent.change(screen.getByLabelText(copy.sandboxAccounts), { target: { value: 'page-1\n\n page-2 ' } });
    fireEvent.click(screen.getByLabelText(copy.registrySwitch));
    fireEvent.click(screen.getByRole('button', { name: copy.saveSettings }));

    expect(await screen.findByText(copy.settingsSaved)).toBeInTheDocument();
    expect(calls.find((call) => call.method === 'PUT')?.body).toEqual({
      chatAllowanceDefault: 750,
      chatAllowanceByProfessionalType: { TYPE_A: 500, TYPE_B: 200 },
      instagramConnectEnabled: true,
      publishSandboxOnly: false,
      sandboxAccountIds: ['page-1', 'page-2'],
      registryReadsEnabled: true,
    });
  });

  it('asks for a fresh strong sign-in when the Founder’s change is refused for step-up, and says plainly when it failed', async () => {
    let status = 403;
    install({
      'GET share': () => reply(200, { days: [], relationshipsCounted: 0, assistantShare: null }),
      'GET attention': () => reply(200, []),
      'PUT settings': () => reply(status, {}),
    });
    render(<AgentOperationSettings copy={copy} initial={initial} />);

    fireEvent.click(screen.getByRole('button', { name: copy.saveSettings }));
    expect(await screen.findByText(copy.stepUpNeeded)).toBeInTheDocument();
    status = 500;
    fireEvent.click(screen.getByRole('button', { name: copy.saveSettings }));
    expect(await screen.findByText(copy.failed)).toBeInTheDocument();
  });

  it('refuses an invalid allowance or override before anything is sent', async () => {
    const calls = install({
      'GET share': () => reply(200, { days: [], relationshipsCounted: 0, assistantShare: null }),
      'GET attention': () => reply(200, []),
    });
    render(<AgentOperationSettings copy={copy} initial={initial} />);

    fireEvent.change(screen.getByLabelText(copy.allowanceDefault), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: copy.saveSettings }));
    expect(await screen.findByText(/whole number from 1 to 1,000,000/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(copy.allowanceDefault), { target: { value: '10' } });
    fireEvent.change(screen.getByLabelText(copy.allowanceByType), { target: { value: 'TYPE_A=oops' } });
    fireEvent.click(screen.getByRole('button', { name: copy.saveSettings }));

    expect(screen.getByText(/whole number from 1 to 1,000,000/)).toBeInTheDocument();
    expect(calls.some((call) => call.method === 'PUT')).toBe(false);
  });

  it('says when the service could not be reached', async () => {
    global.fetch = jest.fn(async () => {
      throw new Error('offline');
    }) as jest.Mock;
    render(<AgentOperationSettings copy={copy} initial={initial} />);

    fireEvent.click(screen.getByRole('button', { name: copy.saveSettings }));

    expect(await screen.findByText(copy.failed)).toBeInTheDocument();
    expect(await screen.findAllByText(copy.nothingYet)).toHaveLength(2);
  });

  it('shows how work is reached as a trend with counts only, and what needs the operator', async () => {
    install({
      'GET share': () =>
        reply(200, {
          days: [
            { day: '2026-12-01', asked: 1, accepted: 1, tool: 1, assistantShare: 0.6667 },
            { day: '2026-12-02', asked: 0, accepted: 0, tool: 0, assistantShare: null },
          ],
          relationshipsCounted: 2,
          assistantShare: 0.6667,
        }),
      'GET attention': () =>
        reply(200, [{ relationshipRef: 'abc123', metric: 'PUBLISH_FAILED', total: 2, lastDay: '2026-12-01' }]),
    });
    render(<AgentOperationSettings copy={copy} initial={initial} />);

    expect(await screen.findByText('67% · 2')).toBeInTheDocument();
    expect(screen.getByText(copy.shareNote)).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /2026-12-01/ })).toHaveTextContent('67%');
    expect(screen.getByRole('row', { name: /2026-12-02/ })).toHaveTextContent('—');
    expect(screen.getByText(/publish failed × 2 · abc123 · 2026-12-01/)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(copy.nothingYet)).not.toBeInTheDocument());
  });
});
