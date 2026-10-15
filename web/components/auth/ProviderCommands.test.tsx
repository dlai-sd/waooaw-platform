import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { ProviderCommands } from './ProviderCommands';
import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const providers: IdentityProvider[] = [
  { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'AVAILABLE' },
  {
    id: 'FACEBOOK',
    displayName: 'Facebook',
    authenticationPath: 'META',
    availability: 'UNAVAILABLE',
    unavailableReason: 'NOT_CONFIGURED',
  },
  {
    id: 'APPLE',
    displayName: 'Apple',
    authenticationPath: 'APPLE',
    availability: 'UNAVAILABLE',
    unavailableReason: 'NOT_CONFIGURED',
  },
  {
    id: 'EMAIL',
    displayName: 'Email',
    authenticationPath: 'CREDENTIAL',
    availability: 'UNAVAILABLE',
    unavailableReason: 'NOT_CONFIGURED',
  },
];

describe('ProviderCommands', () => {
  beforeEach(() => {
    jest.mocked(signIn).mockReset();
  });

  it('starts Google account selection directly', async () => {
    render(<ProviderCommands callbackUrl="/home" intent="login" providers={providers} />);

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Google' }));

    await waitFor(() =>
      expect(signIn).toHaveBeenCalledWith(
        'keycloak-google',
        { callbackUrl: '/home', waooawIntent: 'LOGIN' },
        { max_age: '0', prompt: 'select_account' }
      )
    );
    expect(screen.getByRole('button', { name: 'Log in with Facebook (Unavailable)' })).toBeDisabled();
  });

  it('clears a denied session through Keycloak logout before retrying a provider', async () => {
    const navigate = jest.fn();
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ logoutPath: '/api/auth/keycloak-logout?nonce=recovery' }),
    });
    Object.defineProperty(globalThis, 'fetch', { configurable: true, value: fetchMock });
    sessionStorage.setItem('waooaw:identity:registration-draft', '{"displayName":"Prior customer"}');
    render(
      <ProviderCommands
        callbackUrl="/home"
        intent="login"
        navigate={navigate}
        providers={providers}
        resetSessionBeforeLaunch
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Google' }));

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/api/auth/keycloak-logout?nonce=recovery'));
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/keycloak-logout', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ command: 'ACCOUNT_SWITCH' }),
    });
    expect(sessionStorage.getItem('waooaw:identity:registration-draft')).toBeNull();
    expect(signIn).not.toHaveBeenCalled();
  });

  it('does not launch a broker when denied-session logout cannot start', async () => {
    const navigate = jest.fn();
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: jest.fn().mockResolvedValue({ ok: false }),
    });
    render(
      <ProviderCommands
        callbackUrl="/home"
        intent="login"
        navigate={navigate}
        providers={providers}
        resetSessionBeforeLaunch
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Google' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Google sign-in could not start.');
    expect(navigate).not.toHaveBeenCalled();
    expect(signIn).not.toHaveBeenCalled();
  });

  it('orders provider icon controls into customer scanning order', () => {
    render(<ProviderCommands callbackUrl="/login" intent="login" providers={[...providers].reverse()} />);

    expect(screen.getAllByRole('button').map((button) => button.getAttribute('aria-label'))).toEqual([
      'Log in with Google',
      'Log in with Facebook (Unavailable)',
      'Log in with Apple (Unavailable)',
      'Log in with Email (Unavailable)',
    ]);
    expect(screen.getByText('Log in with Google')).toHaveClass('visually-hidden');
  });

  it('does not start unavailable providers', () => {
    render(<ProviderCommands callbackUrl="/register" intent="register" providers={providers} />);

    expect(screen.getByRole('button', { name: 'Sign up with Apple (Unavailable)' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Sign up with Email (Unavailable)' })).toBeDisabled();
    expect(signIn).not.toHaveBeenCalled();
  });

  it('keeps an unsupported provider non-actionable even when projected as available', () => {
    render(
      <ProviderCommands
        callbackUrl="/register"
        intent="register"
        providers={[{ id: 'APPLE', displayName: 'Apple', authenticationPath: 'APPLE', availability: 'AVAILABLE' }]}
      />
    );

    expect(screen.getByRole('button', { name: 'Sign up with Apple (Unavailable)' })).toBeDisabled();
  });

  it('restores provider controls when sign-in cannot start', async () => {
    jest.mocked(signIn).mockRejectedValueOnce(new Error('navigation unavailable'));
    render(
      <ProviderCommands
        callbackUrl="/login"
        intent="login"
        providers={[providers[0], { ...providers[1], availability: 'AVAILABLE', unavailableReason: undefined }]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Google' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Log in with Google' })).toBeEnabled());
    expect(screen.getByRole('alert')).toHaveAttribute('data-reason-code', 'BROKER_LAUNCH_FAILED');
    expect(screen.getByRole('button', { name: 'Log in with Facebook' })).toBeEnabled();
  });

  it('reports Facebook launch failures truthfully', async () => {
    jest.mocked(signIn).mockRejectedValueOnce(new Error('navigation unavailable'));
    render(
      <ProviderCommands
        callbackUrl="/login"
        intent="login"
        providers={[providers[0], { ...providers[1], availability: 'AVAILABLE', unavailableReason: undefined }]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Facebook' }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Facebook sign-in could not start.'));
    expect(screen.getByRole('alert')).toHaveAttribute('data-reason-code', 'BROKER_LAUNCH_FAILED');
  });

  it('starts Facebook broker sign-in without an intermediate local sign-out page', async () => {
    render(
      <ProviderCommands
        callbackUrl="/home"
        intent="login"
        providers={[{ ...providers[1], availability: 'AVAILABLE', unavailableReason: undefined }]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Facebook' }));

    await waitFor(() =>
      expect(signIn).toHaveBeenCalledWith(
        'keycloak-facebook',
        { callbackUrl: '/home', waooawIntent: 'LOGIN' },
        undefined
      )
    );
  });

  it('offers an actionable retry when provider readiness is temporarily unavailable', () => {
    const reload = jest.fn();
    render(
      <ProviderCommands
        callbackUrl="/register"
        intent="register"
        providers={providers.map((provider) => ({
          ...provider,
          availability: 'UNAVAILABLE',
          unavailableReason: 'TEMPORARILY_UNAVAILABLE',
        }))}
        reload={reload}
      />
    );

    expect(screen.getByText('Sign-in services are still starting.')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('keeps every provider visible and disabled while readiness is pending', () => {
    render(
      <ProviderCommands
        callbackUrl="/login"
        intent="login"
        providers={providers.map((provider) => ({ ...provider, availability: 'AVAILABLE' }))}
        readinessPending
      />
    );

    expect(screen.getAllByRole('button')).toHaveLength(4);
    for (const button of screen.getAllByRole('button')) expect(button).toBeDisabled();
    expect(screen.queryByText('Sign-in services are still starting.')).not.toBeInTheDocument();
  });
});
