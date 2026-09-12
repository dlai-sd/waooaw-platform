import { render, screen } from '@testing-library/react';
import { getServerSession } from 'next-auth';
import { LoginView } from './LoginView';
import { RegisterView } from './RegisterView';
import { listIdentityProviders } from '@/lib/api/identity';
import { getRequestI18n } from '@/lib/i18n-server';
import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';

jest.mock('next-auth', () => ({ getServerSession: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ listIdentityProviders: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('./ProviderCommands', () => ({
  ProviderCommands: ({ callbackUrl, providers }: { callbackUrl: string; providers: IdentityProvider[] }) => (
    <div data-testid="provider-commands" data-callback-url={callbackUrl}>{providers.length} providers</div>
  ),
}));
jest.mock('./RegistrationFlow', () => ({
  RegistrationFlow: ({ locale, returnTo }: { locale: string; returnTo: string }) => (
    <div data-testid="registration-flow" data-return-to={returnTo}>{locale}</div>
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
      secureAccess: 'Secure access',
      welcomeBack: 'Welcome back',
      identityBrokerDescription: 'Brokered identity',
      newToWaaoaw: 'New to WAOOAW?',
      createAccount: 'Create account',
    },
  } as Awaited<ReturnType<typeof getRequestI18n>>);
  jest.mocked(listIdentityProviders).mockResolvedValue(providers);
  jest.mocked(getServerSession).mockResolvedValue(null);
});

describe('authentication views', () => {
  it('renders login providers with a safe callback target', async () => {
    render(await LoginView({ searchParams: Promise.resolve({ returnTo: 'https://example.com' }) }));

    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-callback-url', '/register?returnTo=%2Fhome');
    expect(screen.getByRole('link', { name: 'Create account' })).toHaveAttribute('href', '/register?returnTo=%2Fhome');
  });

  it('preserves a safe protected target through registration', async () => {
    render(await LoginView({ searchParams: Promise.resolve({ returnTo: '/settings' }) }));

    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-callback-url', '/register?returnTo=%2Fsettings');
  });

  it('offers projected providers before registration authentication', async () => {
    render(await RegisterView());

    expect(screen.getByRole('heading', { name: 'Create your WAOOAW account' })).toBeInTheDocument();
    expect(screen.getByTestId('provider-commands')).toHaveAttribute('data-callback-url', '/register?returnTo=%2Fhome');
    expect(listIdentityProviders).toHaveBeenCalledTimes(1);
  });

  it('reuses the registration flow for an authenticated session', async () => {
    jest.mocked(getServerSession).mockResolvedValue({ authenticated: true } as never);

    render(await RegisterView({ searchParams: Promise.resolve({ returnTo: '/settings' }) }));

    expect(screen.getByTestId('registration-flow')).toHaveTextContent('en');
    expect(screen.getByTestId('registration-flow')).toHaveAttribute('data-return-to', '/settings');
    expect(screen.queryByTestId('provider-commands')).not.toBeInTheDocument();
    expect(listIdentityProviders).not.toHaveBeenCalled();
  });
});