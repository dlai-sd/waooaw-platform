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
  beforeEach(() => jest.mocked(signIn).mockReset());

  it('requires explicit disclosure before starting Google account selection', () => {
    render(<ProviderCommands callbackUrl="/home" intent="login" providers={providers} />);

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Google' }));

    expect(screen.getByRole('dialog', { name: 'Continue to Google' })).toBeVisible();
    expect(
      screen.getByText(
        /WAOOAW will receive your name, email address, profile information and Google account identifier/
      )
    ).toBeVisible();
    expect(screen.getByText(/WAOOAW does not receive your Google password/)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Privacy Notice' })).toHaveAttribute('href', '/privacy');
    expect(signIn).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Continue to Google' }));

    expect(signIn).toHaveBeenCalledWith('keycloak-google', { callbackUrl: '/home' }, { prompt: 'select_account' });
    expect(screen.getByRole('button', { name: 'Log in with Facebook (Unavailable)' })).toBeDisabled();
  });

  it('cancels Google disclosure without provider handoff', () => {
    render(<ProviderCommands callbackUrl="/home" intent="login" providers={providers} />);

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Google' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByRole('dialog', { name: 'Continue to Google' })).not.toBeInTheDocument();
    expect(signIn).not.toHaveBeenCalled();
  });

  it('contains disclosure focus and restores the Google command on Escape', () => {
    render(<ProviderCommands callbackUrl="/home" intent="login" providers={providers} />);
    const google = screen.getByRole('button', { name: 'Log in with Google' });
    fireEvent.click(google);
    const continueCommand = screen.getByRole('button', { name: 'Continue to Google' });
    const privacy = screen.getByRole('link', { name: 'Privacy Notice' });

    expect(continueCommand).toHaveFocus();
    fireEvent.keyDown(window, { key: 'Tab' });
    expect(privacy).toHaveFocus();
    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
    expect(continueCommand).toHaveFocus();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(google).toHaveFocus();
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
    fireEvent.click(screen.getByRole('button', { name: 'Continue to Google' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Log in with Google' })).toBeEnabled());
    expect(screen.getByRole('alert')).toHaveAttribute('data-reason-code', 'BROKER_LAUNCH_FAILED');
    expect(screen.getByRole('button', { name: 'Log in with Facebook' })).toBeEnabled();
  });

  it('discloses Facebook data use and reports Facebook launch failures truthfully', async () => {
    jest.mocked(signIn).mockRejectedValueOnce(new Error('navigation unavailable'));
    render(
      <ProviderCommands
        callbackUrl="/login"
        intent="login"
        providers={[providers[0], { ...providers[1], availability: 'AVAILABLE', unavailableReason: undefined }]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Log in with Facebook' }));
    expect(screen.getByRole('dialog', { name: 'Continue to Facebook' })).toBeVisible();
    expect(screen.getByText(/Facebook account identifier/)).toBeVisible();
    expect(signIn).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Continue to Facebook' }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Facebook sign-in could not start.'));
    expect(screen.getByRole('alert')).toHaveAttribute('data-reason-code', 'BROKER_LAUNCH_FAILED');
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
});
