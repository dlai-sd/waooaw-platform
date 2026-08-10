// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { fireEvent, render, screen } from '@testing-library/react';
import { signIn, signOut } from 'next-auth/react';
import { AccountSwitchCommand, SignOutCommand } from './SignOutCommand';

jest.mock('next-auth/react', () => ({ signIn: jest.fn(), signOut: jest.fn() }));

it('clears WAOOAW protected state before ending the session', () => {
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
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
  expect(sessionStorage.getItem('waooaw:identity:registration-draft')).toBeNull();
  expect(Object.keys(localStorage).filter((key) => key.startsWith('waooaw:conversation:'))).toEqual([]);
  expect(localStorage.getItem('waooaw:preference:theme')).toBeNull();
  expect(sessionStorage.getItem('other-app')).toBe('preserve');
  expect(localStorage.getItem('other-app-preference')).toBe('preserve');
  expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/' });
});

it('clears protected state before requesting a different Keycloak account', () => {
  sessionStorage.setItem('waooaw:relationship:draft', 'prior customer text');
  localStorage.setItem('waooaw:conversation:relationship-b:draft', 'prior account text');
  localStorage.setItem('unrelated-preference', 'retain');
  render(<AccountSwitchCommand label="Switch account" />);
  fireEvent.click(screen.getByRole('button', { name: 'Switch account' }));
  expect(sessionStorage.getItem('waooaw:relationship:draft')).toBeNull();
  expect(localStorage.getItem('waooaw:conversation:relationship-b:draft')).toBeNull();
  expect(localStorage.getItem('unrelated-preference')).toBe('retain');
  expect(signIn).toHaveBeenCalledWith('keycloak', { callbackUrl: '/home' }, { prompt: 'select_account' });
});