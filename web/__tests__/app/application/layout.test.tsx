import { render, screen } from '@testing-library/react';
import { redirect } from 'next/navigation';
import ApplicationLayout from '@/app/(application)/layout';
import { getIdentitySession } from '@/lib/api/identity';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';

jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/components/shell/ProtectedAppShell', () => ({
  ProtectedAppShell: ({ children, identitySession }: { children: React.ReactNode; identitySession?: unknown }) => (
    <div data-has-membership={identitySession !== undefined} data-testid="application-shell">
      {children}
    </div>
  ),
}));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
  jest.mocked(getRequestI18n).mockResolvedValue({ locale: 'en', messages: {} } as never);
  jest.mocked(redirect).mockImplementation(() => {
    throw new Error('NEXT_REDIRECT');
  });
});

it('allows an authenticated visitor to browse without customer registration', async () => {
  jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'registration-required' });

  render(await ApplicationLayout({ children: <p>Marketplace</p> }));

  expect(redirect).not.toHaveBeenCalled();
  expect(screen.getByTestId('application-shell')).toHaveAttribute('data-has-membership', 'false');
  expect(screen.getByText('Marketplace')).toBeVisible();
});

it('keeps anonymous users outside the application shell', async () => {
  jest.mocked(getServerAccessToken).mockResolvedValue(undefined);

  await expect(ApplicationLayout({ children: <p>Marketplace</p> })).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/login');
  expect(getIdentitySession).not.toHaveBeenCalled();
});

it('renders a forbidden state for action denial without exposing protected content', async () => {
  jest.mocked(getIdentitySession).mockResolvedValue({
    kind: 'forbidden',
    code: 'IDENTITY_ACTION_DENIED',
    correlationId: 'd8f914cf-f258-46f3-a41a-e345d489862a',
  });
  jest.mocked(getRequestI18n).mockResolvedValue({
    locale: 'en',
    messages: {
      retrySecureSignIn: 'Sign in again',
      accessNotPermitted: 'Access not permitted',
      accessNotPermittedDescription: 'Your current session cannot access this workspace.',
    },
  } as never);

  render(await ApplicationLayout({ children: <p>Protected customer data</p> }));

  expect(screen.getByRole('heading', { name: 'Access not permitted' })).toBeVisible();
  expect(screen.queryByText('Protected customer data')).not.toBeInTheDocument();
});
