import { fireEvent, render, waitFor } from '@testing-library/react';
import { signOut } from 'next-auth/react';
import { identitySessionChangeKey } from './SignOutCommand';
import { SessionValidityGuard } from './SessionValidityGuard';

jest.mock('next-auth/react', () => ({ signOut: jest.fn() }));

beforeEach(() => {
  jest.mocked(signOut).mockReset().mockResolvedValue({ url: '' });
});

afterEach(() => {
  Reflect.deleteProperty(globalThis, 'fetch');
});

it.each([401, 403])('clears a backend-revoked session on focus (%s)', async (status) => {
  Object.defineProperty(globalThis, 'fetch', {
    configurable: true,
    value: jest.fn().mockResolvedValue({ status }),
  });
  render(<SessionValidityGuard />);

  fireEvent.focus(window);

  await waitFor(() => expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/login' }));
});

it('does not claim logout when session validation is temporarily unavailable', async () => {
  Object.defineProperty(globalThis, 'fetch', {
    configurable: true,
    value: jest.fn().mockResolvedValue({ status: 503 }),
  });
  render(<SessionValidityGuard />);

  fireEvent.focus(window);

  await waitFor(() => expect(fetch).toHaveBeenCalled());
  expect(signOut).not.toHaveBeenCalled();
});

it('clears other tabs when a same-browser session change is announced', async () => {
  render(<SessionValidityGuard />);

  window.dispatchEvent(
    new StorageEvent('storage', {
      key: identitySessionChangeKey,
      newValue: JSON.stringify({ action: 'SIGN_OUT', nonce: crypto.randomUUID() }),
      storageArea: localStorage,
    })
  );

  await waitFor(() => expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/login' }));
});