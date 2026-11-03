import ApplicationLayout from '@/app/(application)/layout';
import type { IdentitySession } from '@/lib/api/generated/models/IdentitySession';
import type { WorkspaceLayoutPreferencesV1 } from '@/lib/api/generated/models/WorkspaceLayoutPreferencesV1';
import { getIdentitySession, getWorkspaceLayoutPreferences } from '@/lib/api/identity';
import { getMessages } from '@/lib/i18n';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';
import { logServerFailure } from '@/lib/server-failure';
import { render, screen } from '@testing-library/react';
import { redirect } from 'next/navigation';

jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn(), getWorkspaceLayoutPreferences: jest.fn() }));
jest.mock('@/lib/server-failure', () => ({ logServerFailure: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/components/shell/ProtectedAppShell', () => ({
  ProtectedAppShell: ({
    children,
    identitySession,
    workspaceLayout,
  }: { children: React.ReactNode; identitySession?: unknown; workspaceLayout?: WorkspaceLayoutPreferencesV1 }) => (
    <div
      data-has-membership={identitySession !== undefined}
      data-layout-version={workspaceLayout?.preferenceVersion}
      data-testid="application-shell"
    >
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

it('renders the basic customer shell for a broker-authenticated visitor without registering them', async () => {
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

it('preserves registered identity and exposes retry instead of crashing on preferences failure', async () => {
  const session: IdentitySession = {
    accountReference: 'account',
    roles: new Set(),
    capabilities: new Set(),
    assuranceLevel: 'AAL2_ACCOUNT',
    authenticationPath: 'PORTAL',
    emailVerified: true,
    mobileVerified: false,
    authenticatedAt: new Date(),
    expiresAt: new Date(Date.now() + 60000),
    nextAction: 'NONE',
  };
  jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'ready', session });
  const failure = new Error('preferences unavailable');
  jest.mocked(getWorkspaceLayoutPreferences).mockRejectedValue(failure);
  const messages = getMessages('en');
  jest.mocked(getRequestI18n).mockResolvedValue({ locale: 'en', messages });

  const failedView = render(await ApplicationLayout({ children: <p>Protected content</p> }));

  expect(screen.getByTestId('application-shell')).toHaveAttribute('data-has-membership', 'true');
  expect(screen.getByRole('heading', { name: messages.globalErrorTitle })).toBeVisible();
  expect(screen.getByText(messages.workspacePreferencesUnavailable)).toBeVisible();
  expect(screen.getByRole('link', { name: messages.tryAgain })).toHaveAttribute('href', '/home');
  expect(screen.queryByText('Protected content')).not.toBeInTheDocument();
  expect(logServerFailure).toHaveBeenCalledWith('web.identity.workspace_layout_load_failed', failure);
  expect(redirect).not.toHaveBeenCalled();
  failedView.unmount();
  jest.mocked(getWorkspaceLayoutPreferences).mockResolvedValue({
    schemaVersion: '1',
    preferenceVersion: 7,
    navigationVisibility: 'VISIBLE',
    progressVisibility: 'VISIBLE',
    conversationWidthPercent: 50,
    reduceMotion: false,
    updatedAt: new Date(),
  });
  render(await ApplicationLayout({ children: <p>Protected content</p> }));
  expect(screen.getByText('Protected content')).toBeVisible();
  expect(screen.getByTestId('application-shell')).toHaveAttribute('data-layout-version', '7');
  expect(getWorkspaceLayoutPreferences).toHaveBeenNthCalledWith(2, 'access-token');
  expect(logServerFailure).toHaveBeenCalledTimes(1);
  expect(redirect).not.toHaveBeenCalled();
});
