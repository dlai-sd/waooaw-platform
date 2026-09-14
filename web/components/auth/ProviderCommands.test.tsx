import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { ProviderCommands } from './ProviderCommands';
import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const providers: IdentityProvider[] = [
  { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'AVAILABLE' },
  { id: 'FACEBOOK', displayName: 'Facebook', authenticationPath: 'META', availability: 'UNAVAILABLE', unavailableReason: 'NOT_CONFIGURED' },
  { id: 'APPLE', displayName: 'Apple', authenticationPath: 'APPLE', availability: 'UNAVAILABLE', unavailableReason: 'NOT_CONFIGURED' },
  { id: 'EMAIL', displayName: 'Email', authenticationPath: 'CREDENTIAL', availability: 'UNAVAILABLE', unavailableReason: 'NOT_CONFIGURED' },
];

describe('ProviderCommands', () => {
  beforeEach(() => jest.mocked(signIn).mockReset());

  it('starts only an available brokered provider', () => {
    render(<ProviderCommands callbackUrl="/home" intent="login" providers={providers} />);

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Google' }));

    expect(signIn).toHaveBeenCalledWith('keycloak-google', { callbackUrl: '/home' });
    expect(screen.getByRole('button', { name: 'Log in with Facebook (Unavailable)' })).toBeDisabled();
  });

  it('does not start unavailable providers', () => {
    render(<ProviderCommands callbackUrl="/register" intent="register" providers={providers} />);

    expect(screen.getByRole('button', { name: 'Sign up with Apple (Unavailable)' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Sign up with Email (Unavailable)' })).toBeDisabled();
    expect(signIn).not.toHaveBeenCalled();
  });

  it('keeps an unsupported provider non-actionable even when projected as available', () => {
    render(<ProviderCommands callbackUrl="/register" intent="register" providers={[
      { id: 'APPLE', displayName: 'Apple', authenticationPath: 'APPLE', availability: 'AVAILABLE' },
    ]} />);

    expect(screen.getByRole('button', { name: 'Sign up with Apple (Unavailable)' })).toBeDisabled();
  });

  it('restores provider controls when sign-in cannot start', async () => {
    jest.mocked(signIn).mockRejectedValueOnce(new Error('navigation unavailable'));
    render(<ProviderCommands callbackUrl="/login" intent="login" providers={[
      providers[0],
      { ...providers[1], availability: 'AVAILABLE', unavailableReason: undefined },
    ]} />);

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Google' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Log in with Google' })).toBeEnabled());
    expect(screen.getByRole('button', { name: 'Log in with Facebook' })).toBeEnabled();
  });
});