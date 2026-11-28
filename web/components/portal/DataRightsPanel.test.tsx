// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-049, C-059, C-063, C-078

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DataRightsPanel } from './DataRightsPanel';

function install(handler: (url: string, init?: RequestInit) => { status: number; body: unknown }) {
  const calls: Array<{ url: string; method: string; headers: Record<string, string>; body: unknown }> = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({
      url: String(input),
      method: init?.method ?? 'GET',
      headers: (init?.headers ?? {}) as Record<string, string>,
      body: init?.body ? JSON.parse(String(init.body)) : null,
    });
    const { status, body } = handler(String(input), init);
    return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
  }) as jest.Mock;
  return calls;
}

describe('DataRightsPanel', () => {
  it('sends a copy request with an idempotency key and shows its status', async () => {
    let created = false;
    const calls = install((_url, init) => {
      if (init?.method === 'POST') {
        created = true;
        return { status: 201, body: {} };
      }
      return {
        status: 200,
        body: {
          items: created
            ? [{ requestId: 'r1', kind: 'EXPORT', state: 'RECEIVED', requestedAt: '2026-11-30T10:00:00Z' }]
            : [],
        },
      };
    });
    render(<DataRightsPanel />);
    await waitFor(() => expect(calls.length).toBeGreaterThan(0));
    fireEvent.click(screen.getByRole('button', { name: 'Ask for a copy of my data' }));
    expect(await screen.findByText(/Copy of your data: Received/)).toBeInTheDocument();
    const post = calls.find((call) => call.method === 'POST');
    expect(post?.body).toEqual({ schemaVersion: '1.0.0', kind: 'EXPORT' });
    expect(post?.headers['Idempotency-Key']).toMatch(/^[0-9a-f-]{36}$/);
    expect(screen.getByRole('button', { name: 'Ask for a copy of my data' })).toBeDisabled();
  });

  it('asks the customer to confirm before an erasure request is sent', async () => {
    const calls = install(() => ({ status: 200, body: { items: [] } }));
    render(<DataRightsPanel />);
    await waitFor(() => expect(calls.length).toBe(1));
    fireEvent.click(screen.getByRole('button', { name: 'Ask for my account to be erased' }));
    expect(screen.getByRole('alert')).toHaveTextContent('cannot be undone');
    expect(calls.some((call) => call.method === 'POST')).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'No, keep my account' }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('says plainly when only the owner may ask', async () => {
    install((_url, init) =>
      init?.method === 'POST' ? { status: 403, body: {} } : { status: 200, body: { items: [] } }
    );
    render(<DataRightsPanel />);
    fireEvent.click(await screen.findByRole('button', { name: 'Ask for a copy of my data' }));
    expect(await screen.findByText('Only the account owner can ask for this.')).toBeInTheDocument();
  });
});
