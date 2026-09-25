// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn, signOut } from 'next-auth/react';
import { AccountSwitchCommand, SignOutCommand } from './SignOutCommand';

jest.mock('next-auth/react', () => ({ signIn: jest.fn(), signOut: jest.fn() }));

beforeEach(() => {
  jest.mocked(signIn).mockReset();
  jest.mocked(signOut).mockReset().mockResolvedValue({ url: '' });
});

afterEach(() => {
  jest.restoreAllMocks();
  Reflect.deleteProperty(globalThis, 'fetch');
});

it('clears WAOOAW protected state before ending the session', () => {
  const fetchMock = jest.fn().mockReturnValue(new Promise(() => undefined));
  Object.defineProperty(globalThis, 'fetch', { configurable: true, value: fetchMock });
  sessionStorage.setItem('waooaw:identity:registration-draft', '{"displayName":"Asha"}');
  localStorage.setItem('waooaw:conversation:relationship-a:draft', 'protected draft');
  localStorage.setItem('waooaw:conversation:relationship-a:outbox', 'protected outbox');
  localStorage.setItem('waooaw:conversation:relationship-a:retry:message-a', 'protected retry identity');
  localStorage.setItem('waooaw:conversation:relationship-a:cancel:execution-a', 'protected cancellation identity');
  localStorage.setItem('waooaw:conversation:relationship-a:stream-cursor', 'protected stream cursor');
  sessionStorage.setItem('other-app', 'preserve');
  localStorage.setItem('waooaw:preference:theme', 'dark');
  localStorage.setItem('other-app-preference', 'preserve');
  render(<SignOutCommand label="Sign out" />);
  const button = screen.getByRole('button', { name: 'Sign out' });
  fireEvent.click(button);
  expect(sessionStorage.getItem('waooaw:identity:registration-draft')).toBeNull();
  expect(Object.keys(localStorage).filter((key) => key.startsWith('waooaw:conversation:'))).toEqual([]);
  expect(localStorage.getItem('waooaw:preference:theme')).toBeNull();
  expect(localStorage.getItem('waooaw:identity:session-change')).toBeNull();
  expect(sessionStorage.getItem('other-app')).toBe('preserve');
  expect(localStorage.getItem('other-app-preference')).toBe('preserve');
  expect(fetchMock).toHaveBeenCalledWith('/api/auth/keycloak-logout', {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
});

it('revokes prior server sessions before requesting a different Keycloak account', async () => {
  const fetchMock = jest.fn().mockResolvedValue({ ok: true });
  Object.defineProperty(globalThis, 'fetch', { configurable: true, value: fetchMock });
  sessionStorage.setItem('waooaw:relationship:draft', 'prior customer text');
  localStorage.setItem('waooaw:conversation:relationship-b:draft', 'prior account text');
  localStorage.setItem('unrelated-preference', 'retain');
  render(<AccountSwitchCommand label="Switch account" />);
  fireEvent.click(screen.getByRole('button', { name: 'Switch account' }));
  expect(sessionStorage.getItem('waooaw:relationship:draft')).toBeNull();
  expect(localStorage.getItem('waooaw:conversation:relationship-b:draft')).toBeNull();
  expect(localStorage.getItem('waooaw:identity:session-change')).toBeNull();
  expect(localStorage.getItem('unrelated-preference')).toBe('retain');
  expect(fetchMock).toHaveBeenCalledWith('/api/identity/sessions', expect.objectContaining({ method: 'DELETE' }));
  await waitFor(() =>
    expect(signIn).toHaveBeenCalledWith('keycloak-google', { callbackUrl: '/home' }, { prompt: 'select_account' })
  );
  expect(signOut).toHaveBeenCalledWith({ redirect: false });
});

it.each([401, 403])('switches account when prior backend authority is already absent (%s)', async (status) => {
  Object.defineProperty(globalThis, 'fetch', {
    configurable: true,
    value: jest.fn().mockResolvedValue({ ok: false, status }),
  });
  render(<AccountSwitchCommand label="Switch account" />);

  fireEvent.click(screen.getByRole('button', { name: 'Switch account' }));

  await waitFor(() => expect(signOut).toHaveBeenCalledWith({ redirect: false }));
  expect(signIn).toHaveBeenCalledWith('keycloak-google', { callbackUrl: '/home' }, { prompt: 'select_account' });
});

it('does not launch account selection when prior-session revocation fails', async () => {
  jest.mocked(signIn).mockClear();
  Object.defineProperty(globalThis, 'fetch', {
    configurable: true,
    value: jest.fn().mockResolvedValue({ ok: false, status: 503 }),
  });
  render(<AccountSwitchCommand label="Switch account" />);

  fireEvent.click(screen.getByRole('button', { name: 'Switch account' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('Account switch could not start. Try again.');
  expect(signIn).not.toHaveBeenCalled();
});

it('falls back to local NextAuth sign-out when broker logout cannot start', async () => {
  Object.defineProperty(globalThis, 'fetch', {
    configurable: true,
    value: jest.fn().mockResolvedValue({ ok: false }),
  });
  render(<SignOutCommand label="Sign out" />);

  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));

  await waitFor(() => expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/' }));
});

it('clears local NextAuth after backend revocation without entering the Keycloak logout page', async () => {
  Object.defineProperty(globalThis, 'fetch', {
    configurable: true,
    value: jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ logoutPath: '/api/auth/keycloak-logout?nonce=valid' }),
    }),
  });
  render(<SignOutCommand label="Sign out" />);

  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));

  await waitFor(() => expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/' }));
});
