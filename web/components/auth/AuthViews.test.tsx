import { render, screen } from '@testing-library/react';
import { redirect } from 'next/navigation';
import { LoginView } from './LoginView';
import { RegisterView } from './RegisterView';
import { getIdentitySession, listIdentityProviders } from '@/lib/api/identity';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';
import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';

jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn(), listIdentityProviders: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('./ProviderCommands', () => ({
  ProviderCommands: ({
    callbackUrl,
    intent,
    providers,
  }: { callbackUrl: string; intent: string; providers: IdentityProvider[] }) => (
    <div data-testid="provider-commands" data-callback-url={callbackUrl} data-intent={intent}>
      {providers.length} providers
    </div>
  ),
}));
jest.mock('./RegistrationFlow', () => ({
  RegistrationFlow: ({ locale, returnTo }: { locale: string; returnTo: string }) => (
    <div data-testid="registration-flow" data-return-to={returnTo}>
      {locale}
    </div>
  ),
}));

const providers: IdentityProvider[] = [
  { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'AVAILABLE' },
];

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getRequestI18n).mockResolvedValue({
    locale: 'en',
    messages: {
      login: 'Log in',
      secureAccess: 'Secure access',
      welcomeBack: 'Welcome back',
      identityBrokerDescription: 'Brokered identity',
      newToWaaoaw: 'New to WAOOAW?',
      createAccount: 'Create account',
    },
  } as Awaited<ReturnType<typeof getRequestI18n>>);
  jest.mocked(listIdentityProviders).mockResolvedValue(providers);
  jest.mocked(getServerAccessToken).mockResolvedValue(undefined);
  jest.mocked(redirect).mockImplementation(() => {
    throw new Error('NEXT_REDIRECT');
  });
});

describe('authentication views', () => {
  it('renders login providers with a safe callback target', async () => {
    render(await LoginView({ searchParams: Promise.resolve({ returnTo: 'https://example.com' }) }));

    expect(screen.getByRole('img', { name: 'WAOOAW' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Log in to WAOOAW' })).toBeInTheDocument();
    expect(screen.getByText('Welcome back.')).toBeInTheDocument();
    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-callback-url', '/login?returnTo=%2Fhome');
    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-intent', 'login');
    expect(screen.queryByRole('link', { name: 'Create account' })).not.toBeInTheDocument();
  });

  it('preserves a safe protected target through registration', async () => {
    render(await LoginView({ searchParams: Promise.resolve({ returnTo: '/settings' }) }));

    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-callback-url', '/login?returnTo=%2Fsettings');
  });

  it('requires an authenticated visitor to register before continuing', async () => {
    jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'registration-required' });

    await expect(LoginView({ searchParams: Promise.resolve({ returnTo: '/settings' }) })).rejects.toThrow(
      'NEXT_REDIRECT'
    );

    expect(redirect).toHaveBeenCalledWith('/register?returnTo=%2Fsettings');
    expect(listIdentityProviders).not.toHaveBeenCalled();
  });

  it('falls back to provider login when an authenticated broker session has no access token', async () => {
    render(await LoginView({ searchParams: Promise.resolve({ returnTo: '/settings' }) }));

    expect(getIdentitySession).not.toHaveBeenCalled();
    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-callback-url', '/login?returnTo=%2Fsettings');
  });

  it('continues an existing account to the safe target after broker return', async () => {
    jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'ready', session: {} as never });

    await expect(LoginView({ searchParams: Promise.resolve({ returnTo: '/settings' }) })).rejects.toThrow(
      'NEXT_REDIRECT'
    );

    expect(redirect).toHaveBeenCalledWith('/settings');
    expect(listIdentityProviders).not.toHaveBeenCalled();
  });

  it('offers a fresh provider login when existing session validation is temporarily unavailable', async () => {
    jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'unavailable' });

    render(await LoginView({ searchParams: Promise.resolve({ returnTo: '/settings' }) }));

    expect(redirect).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: 'Log in to WAOOAW' })).toBeInTheDocument();
    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-callback-url', '/login?returnTo=%2Fsettings');
  });

  it('offers projected providers before registration authentication', async () => {
    render(await RegisterView());

    expect(screen.getByRole('img', { name: 'WAOOAW' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Create your WAOOAW account' })).toBeInTheDocument();
    expect(screen.getByText('Start your professional journey.')).toBeInTheDocument();
    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-callback-url', '/register?returnTo=%2Fhome');
    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-intent', 'register');
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login?returnTo=%2Fhome');
    expect(screen.getByRole('link', { name: 'Terms of Service' })).toHaveAttribute('href', '/terms');
    expect(screen.getByRole('link', { name: 'Privacy Policy' })).toHaveAttribute('href', '/privacy');
    expect(listIdentityProviders).toHaveBeenCalledTimes(1);
  });

  it('reuses the registration flow for an authenticated session', async () => {
    jest.mocked(getServerAccessToken).mockResolvedValue('access-token');

    render(await RegisterView({ searchParams: Promise.resolve({ returnTo: '/settings' }) }));

    expect(screen.getByTestId('registration-flow')).toHaveTextContent('en');
    expect(screen.getByTestId('registration-flow')).toHaveAttribute('data-return-to', '/settings');
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    expect(screen.queryByTestId('provider-commands')).not.toBeInTheDocument();
    expect(listIdentityProviders).not.toHaveBeenCalled();
  });
});
