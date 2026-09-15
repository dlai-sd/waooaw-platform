import { render, screen } from '@testing-library/react';
import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import ApplicationLayout from '@/app/(application)/layout';
import { getIdentitySession } from '@/lib/api/identity';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';

jest.mock('next-auth', () => ({ getServerSession: jest.fn() }));
jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/components/shell/ProtectedAppShell', () => ({
  ProtectedAppShell: ({ children, identitySession }: { children: React.ReactNode; identitySession?: unknown }) => (
    <div data-has-membership={identitySession !== undefined} data-testid="application-shell">{children}</div>
  ),
}));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getServerSession).mockResolvedValue({ authenticated: true } as never);
  jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
  jest.mocked(getRequestI18n).mockResolvedValue({ locale: 'en', messages: {} } as never);
  jest.mocked(redirect).mockImplementation(() => { throw new Error('NEXT_REDIRECT'); });
});

it('admits an authenticated visitor without creating workspace membership', async () => {
  jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'registration-required' });

  render(await ApplicationLayout({ children: <p>Marketplace</p> }));

  expect(screen.getByTestId('application-shell')).toHaveAttribute('data-has-membership', 'false');
  expect(screen.getByText('Marketplace')).toBeInTheDocument();
});

it('keeps anonymous users outside the application shell', async () => {
  jest.mocked(getServerSession).mockResolvedValue(null);

  await expect(ApplicationLayout({ children: <p>Marketplace</p> })).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/login');
  expect(getIdentitySession).not.toHaveBeenCalled();
});