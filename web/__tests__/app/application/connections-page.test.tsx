// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R010
// Constitutional basis: C-026, C-059, C-063

import ConnectionsPage from '@/app/(application)/connections/page';
import { render, screen } from '@testing-library/react';

jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn().mockResolvedValue('access-token') }));
jest.mock('@/lib/platform-access-server', () => ({
  resolvePlatformAccess: jest.fn().mockResolvedValue({ administrator: false, founder: false }),
}));
jest.mock('@/components/connections/ConnectionsWorkspace', () => ({
  ConnectionsWorkspace: ({ initialNotice, staff }: { initialNotice?: { text: string } | null; staff?: boolean }) => (
    <p data-testid="workspace" data-staff={String(Boolean(staff))}>
      {initialNotice?.text ?? 'no notice'}
    </p>
  ),
}));

it('renders the Connections heading and passes only a fixed notice from the return address', async () => {
  render(await ConnectionsPage({ searchParams: Promise.resolve({ error: 'denied' }) }));

  expect(screen.getByRole('heading', { level: 1, name: 'Connections' })).toBeInTheDocument();
  expect(screen.getByTestId('workspace')).toHaveTextContent(/cancelled or declined/);
});

it('ignores unknown query text instead of rendering it', async () => {
  render(await ConnectionsPage({ searchParams: Promise.resolve({ error: '<b>owned</b>' }) }));

  expect(screen.getByTestId('workspace')).toHaveTextContent('no notice');
  expect(screen.queryByText(/owned/)).not.toBeInTheDocument();
});
