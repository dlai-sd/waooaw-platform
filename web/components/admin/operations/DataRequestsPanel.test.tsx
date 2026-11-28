// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-049, C-059, C-063, C-078

import { fireEvent, render, screen } from '@testing-library/react';
import { DataRequestsPanel } from './DataRequestsPanel';

const open = {
  requestId: '11111111-1111-4111-8111-111111111111',
  tenantId: 't1',
  kind: 'ERASURE',
  requestedAt: '2026-11-30T10:00:00Z',
};

describe('DataRequestsPanel', () => {
  it('lists open requests and refuses to close one without a note', async () => {
    const fetchMock = jest.fn(
      async () => ({ ok: true, status: 200, json: async () => ({ items: [open] }) }) as Response
    );
    global.fetch = fetchMock as unknown as typeof fetch;
    render(<DataRequestsPanel canResolve />);
    expect(await screen.findByText('Erase account')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Mark done' }));
    expect(screen.getByText(/Write what was done/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('tells the Founder when a fresh sign-in is needed', async () => {
    global.fetch = jest.fn(async (_url: RequestInfo | URL, init?: RequestInit) =>
      init?.method === 'POST'
        ? ({ ok: false, status: 403, json: async () => ({}) } as Response)
        : ({ ok: true, status: 200, json: async () => ({ items: [open] }) } as Response)
    ) as unknown as typeof fetch;
    render(<DataRequestsPanel canResolve />);
    fireEvent.change(await screen.findByLabelText('Note'), { target: { value: 'Erased' } });
    fireEvent.click(screen.getByRole('button', { name: 'Mark done' }));
    expect(await screen.findByText(/fresh strong sign-in/)).toBeInTheDocument();
  });

  it('shows no actions to someone who cannot resolve', async () => {
    global.fetch = jest.fn(
      async () => ({ ok: true, status: 200, json: async () => ({ items: [open] }) }) as Response
    ) as unknown as typeof fetch;
    render(<DataRequestsPanel canResolve={false} />);
    expect(await screen.findByText('Erase account')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Mark done' })).not.toBeInTheDocument();
  });
});
