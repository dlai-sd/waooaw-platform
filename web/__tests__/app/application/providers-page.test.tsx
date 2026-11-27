// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import ProvidersPage from '@/app/(application)/admin/providers/page';
import { loadProviders } from '@/lib/provider-admin-server';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken } from '@/lib/server-auth';
import { render, screen } from '@testing-library/react';
import { redirect } from 'next/navigation';

jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/lib/platform-access-server', () => ({
  resolvePlatformAccess: jest.fn(),
}));
jest.mock('@/lib/provider-admin-server', () => ({ loadProviders: jest.fn() }));
jest.mock('@/components/admin/providers/ProvidersWorkspace', () => ({
  ProvidersWorkspace: ({ initialProviders }: { initialProviders: unknown[] }) => (
    <p data-testid="workspace">{initialProviders.length} providers</p>
  ),
}));

function founderAccess(founder: boolean) {
  jest.mocked(resolvePlatformAccess).mockResolvedValue({ founder, administrator: true } as never);
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
  jest.mocked(redirect).mockImplementation(() => {
    throw new Error('NEXT_REDIRECT');
  });
});

it('sends a visitor without a session home before loading anything', async () => {
  jest.mocked(getServerAccessToken).mockResolvedValue(undefined);

  await expect(ProvidersPage()).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/home');
  expect(loadProviders).not.toHaveBeenCalled();
});

it('sends a pricing administrator who is not the Founder to the not-permitted page without reading the registry', async () => {
  founderAccess(false);

  await expect(ProvidersPage()).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/403');
  expect(loadProviders).not.toHaveBeenCalled();
});

it('sends the caller to the not-permitted page when the owner refuses them', async () => {
  founderAccess(true);
  jest.mocked(loadProviders).mockResolvedValue({ kind: 'forbidden' });

  await expect(ProvidersPage()).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/403');
});

it('shows a graceful state when the Business Platform cannot be reached', async () => {
  founderAccess(true);
  jest.mocked(loadProviders).mockResolvedValue({ kind: 'unavailable' });

  render(await ProvidersPage());

  expect(screen.getByRole('heading', { name: 'Providers are unavailable' })).toBeVisible();
  expect(screen.getByRole('link', { name: /Try again/ })).toHaveAttribute('href', '/admin/providers');
  expect(screen.queryByTestId('workspace')).not.toBeInTheDocument();
});

it('names the page and hands the providers to the workspace for the Founder', async () => {
  founderAccess(true);
  jest.mocked(loadProviders).mockResolvedValue({ kind: 'ready', providers: [{ id: 'p1' }] as never });

  render(await ProvidersPage());

  expect(screen.getByRole('region', { name: 'Providers' })).toBeVisible();
  expect(screen.getByRole('heading', { level: 1, name: 'Providers' })).toBeVisible();
  expect(screen.getByTestId('workspace')).toHaveTextContent('1 providers');
  expect(redirect).not.toHaveBeenCalled();
});
