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

  it('keeps Apple local and explains approved alternatives', () => {
    render(<ProviderCommands callbackUrl="/register" providers={providers} />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Apple' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Apple is coming soon');
    expect(screen.getByRole('alert')).toHaveTextContent('Google or Email');
    expect(screen.getByRole('alert')).not.toHaveTextContent('Facebook or email');
    expect(screen.getByRole('alert')).toHaveTextContent('WhatsApp registration');
    expect(signIn).not.toHaveBeenCalled();
  });
});