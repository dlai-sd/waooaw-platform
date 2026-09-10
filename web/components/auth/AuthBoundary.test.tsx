import { act, fireEvent, render, screen } from '@testing-library/react';
import { AuthBoundary } from './AuthBoundary';

describe('auth loading boundary', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it('announces loading, then exposes a bounded failure and retry', () => {
    const retry = jest.fn();
    render(<AuthBoundary retry={retry} />);
    expect(screen.getByRole('status')).toBeVisible();
    act(() => jest.advanceTimersByTime(15_000));
    expect(screen.getByRole('alert')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(retry).toHaveBeenCalledTimes(1);
  });

  it('renders a provider error without exposing server details', () => {
    render(<AuthBoundary failed retry={jest.fn()} />);
    expect(screen.getByRole('heading', { name: 'Sign in could not be completed' })).toBeVisible();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});