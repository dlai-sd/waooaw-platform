import { fireEvent, render, screen } from '@testing-library/react';
import { AuthBoundary } from './AuthBoundary';

jest.mock('next/navigation', () => ({ useSearchParams: () => new URLSearchParams('returnTo=%2Fsettings') }));
jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

describe('auth loading boundary', () => {
  it('announces loading without inventing a timeout failure', () => {
    render(<AuthBoundary />);
    expect(screen.getByRole('heading', { name: 'Log in to WAOOAW' })).toBeVisible();
    expect(screen.getByRole('img', { name: 'WAOOAW' })).toBeVisible();
    expect(screen.getByRole('status')).toBeVisible();
    expect(screen.getByText('Loading secure sign-in options.')).toBeVisible();
      expect(screen.getByRole('button', { name: 'Log in with Google (Unavailable)' })).toBeDisabled();
      expect(screen.getAllByRole('button')).toHaveLength(4);
      expect(screen.getByText("Don't have an account?")).toBeVisible();
      expect(screen.getByRole('link', { name: 'Register' })).toHaveAttribute(
        'href',
        '/register?returnTo=%2Fsettings'
      );
    expect(screen.queryByText('Preparing the requested view.')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('brands registration loading for the intended journey', () => {
    render(<AuthBoundary intent="register" />);

    expect(screen.getByRole('heading', { name: 'Create your WAOOAW account' })).toBeVisible();
    expect(screen.getByText('Start your professional journey.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Sign up with Google (Unavailable)' })).toBeDisabled();
    expect(screen.getByRole('link', { name: 'Terms of Service' })).toHaveAttribute('href', '/terms');
  });

  it('renders a provider error without exposing server details', () => {
    const retry = jest.fn();
    render(<AuthBoundary failed retry={retry} />);
    expect(screen.getByRole('heading', { name: 'Sign in could not be completed' })).toBeVisible();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(retry).toHaveBeenCalledTimes(1);
  });
});
