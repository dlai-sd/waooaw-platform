import { fireEvent, render, screen } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { ProviderCommands } from './ProviderCommands';
import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const providers: IdentityProvider[] = [
  { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'AVAILABLE' },
  { id: 'FACEBOOK', displayName: 'Facebook', authenticationPath: 'META', availability: 'UNAVAILABLE', unavailableReason: 'NOT_CONFIGURED' },
  { id: 'APPLE', displayName: 'Apple', authenticationPath: 'APPLE', availability: 'UNAVAILABLE', unavailableReason: 'NOT_CONFIGURED' },
  { id: 'EMAIL', displayName: 'Email', authenticationPath: 'CREDENTIAL', availability: 'AVAILABLE' },
];

describe('ProviderCommands', () => {
  beforeEach(() => jest.mocked(signIn).mockClear());

  it('starts only an available brokered provider', () => {
    render(<ProviderCommands callbackUrl="/home" providers={providers} />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    expect(signIn).toHaveBeenCalledWith('keycloak-google', { callbackUrl: '/home' });
    expect(screen.getByRole('button', { name: /Continue with Facebook/ })).toBeDisabled();
  });

  it('groups unavailable providers as non-actionable coming-soon choices', () => {
    render(<ProviderCommands callbackUrl="/register" providers={providers} />);

    fireEvent.click(screen.getByRole('button', { name: /Continue with Apple/ }));

    expect(screen.getByText('Coming soon', { selector: 'p' })).toBeVisible();
    expect(screen.getByRole('button', { name: /Continue with Apple/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Continue with Facebook/ })).toBeDisabled();
    expect(signIn).not.toHaveBeenCalled();
  });

  it('keeps an unsupported provider non-actionable even when projected as available', () => {
    render(<ProviderCommands callbackUrl="/register" providers={[
      { id: 'APPLE', displayName: 'Apple', authenticationPath: 'APPLE', availability: 'AVAILABLE' },
    ]} />);

    expect(screen.getByRole('button', { name: /Continue with Apple.*Coming soon/ })).toBeDisabled();
    expect(screen.getByText('Coming soon', { selector: 'p' })).toBeVisible();
  });
});