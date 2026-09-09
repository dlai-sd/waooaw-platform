import { fireEvent, render, screen } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { AuthDialog } from './AuthDialog';

jest.mock('next/navigation', () => ({ useRouter: jest.fn() }));

describe('AuthDialog', () => {
  const back = jest.fn();
  const router = {
    back,
    forward: jest.fn(),
    refresh: jest.fn(),
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  } as ReturnType<typeof useRouter>;

  beforeAll(() => {
    HTMLDialogElement.prototype.showModal = function showModal() { this.setAttribute('open', ''); };
    HTMLDialogElement.prototype.close = function close() { this.removeAttribute('open'); };
  });

  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(useRouter).mockReturnValue(router);
  });

  it('opens modally, dismisses on Escape, and restores invoking focus', () => {
    const trigger = document.createElement('button');
    document.body.appendChild(trigger);
    trigger.focus();

    const { unmount } = render(<AuthDialog><h1 id="auth-dialog-title">Log in</h1></AuthDialog>);
    const dialog = screen.getByRole('dialog', { name: 'Log in' });
    expect(dialog).toHaveAttribute('open');

    fireEvent(dialog, new Event('cancel', { bubbles: true, cancelable: true }));
    expect(router.replace).toHaveBeenCalledWith('/', { scroll: false });
    expect(back).not.toHaveBeenCalled();

    unmount();
    expect(trigger).toHaveFocus();
    trigger.remove();
  });

  it('dismisses only when the backdrop itself is clicked', () => {
    render(<AuthDialog><h1 id="auth-dialog-title">Register</h1><button type="button">Inside</button></AuthDialog>);
    fireEvent.click(screen.getByRole('button', { name: 'Inside' }));
    expect(router.replace).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('dialog', { name: 'Register' }));
    expect(router.replace).toHaveBeenCalledWith('/', { scroll: false });
  });
});