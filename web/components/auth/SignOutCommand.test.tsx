// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { fireEvent, render, screen } from '@testing-library/react';
import { signIn, signOut } from 'next-auth/react';
import { AccountSwitchCommand, SignOutCommand } from './SignOutCommand';

jest.mock('next-auth/react', () => ({ signIn: jest.fn(), signOut: jest.fn() }));

it('clears WAOOAW protected state before ending the session', () => {
  sessionStorage.setItem('waooaw:identity:registration-draft', '{"displayName":"Asha"}');
  sessionStorage.setItem('other-app', 'preserve');
  render(<SignOutCommand label="Sign out" />);
  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
  expect(sessionStorage.getItem('waooaw:identity:registration-draft')).toBeNull();
  expect(sessionStorage.getItem('other-app')).toBe('preserve');
  expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/' });
});

it('clears protected state before requesting a different Keycloak account', () => {
  sessionStorage.setItem('waooaw:relationship:draft', 'prior customer text');
  render(<AccountSwitchCommand label="Switch account" />);
  fireEvent.click(screen.getByRole('button', { name: 'Switch account' }));
  expect(sessionStorage.getItem('waooaw:relationship:draft')).toBeNull();
  expect(signIn).toHaveBeenCalledWith('keycloak', { callbackUrl: '/home' }, { prompt: 'select_account' });
});