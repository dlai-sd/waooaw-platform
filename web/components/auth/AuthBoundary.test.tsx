import { fireEvent, render, screen } from '@testing-library/react';
import { AuthBoundary } from './AuthBoundary';

describe('auth loading boundary', () => {
  it('announces loading without inventing a timeout failure', () => {
    render(<AuthBoundary />);
    expect(screen.getByRole('heading', { name: 'Log in to WAOOAW' })).toBeVisible();
    expect(screen.getByRole('img', { name: 'WAOOAW' })).toBeVisible();
    expect(screen.getByRole('status')).toBeVisible();
    expect(screen.getByText('Loading secure sign-in options.')).toBeVisible();
    expect(screen.queryByText('Preparing the requested view.')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('brands registration loading for the intended journey', () => {
    render(<AuthBoundary intent="register" />);

    expect(screen.getByRole('heading', { name: 'Create your WAOOAW account' })).toBeVisible();
    expect(screen.getByText('Start your professional journey.')).toBeVisible();
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
