import { render, screen } from '@testing-library/react';
import { redirect } from 'next/navigation';
import CustomerLayout from '@/app/(authenticated)/layout';
import { getIdentitySession } from '@/lib/api/identity';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';

jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/components/shell/ProtectedAppShell', () => ({
  ProtectedAppShell: ({ children, identitySession }: { children: React.ReactNode; identitySession?: unknown }) => (
    <div data-has-membership={identitySession !== undefined} data-testid="customer-shell">{children}</div>
  ),
}));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
  jest.mocked(getRequestI18n).mockResolvedValue({ locale: 'en', messages: {} } as never);
  jest.mocked(redirect).mockImplementation(() => { throw new Error('NEXT_REDIRECT'); });
});

it('admits an authenticated visitor to customer portal routes without membership', async () => {
  jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'registration-required' });

  render(await CustomerLayout({ children: <p>My Agents</p> }));

  expect(screen.getByTestId('customer-shell')).toHaveAttribute('data-has-membership', 'false');
  expect(screen.getByText('My Agents')).toBeInTheDocument();
  expect(redirect).not.toHaveBeenCalled();
});