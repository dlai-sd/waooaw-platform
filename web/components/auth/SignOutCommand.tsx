'use client';

// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { LogOut, RefreshCw } from 'lucide-react';
import { signIn } from 'next-auth/react';

export const identitySessionChangeKey = 'waooaw:identity:session-change';

export function clearProtectedClientState(storages: readonly Storage[] = [window.sessionStorage, window.localStorage]) {
  for (const storage of storages) {
    for (let index = storage.length - 1; index >= 0; index -= 1) {
      const key = storage.key(index);
      if (key?.startsWith('waooaw:')) storage.removeItem(key);
    }
  }
}

function announceIdentitySessionChange(action: 'SIGN_OUT' | 'ACCOUNT_SWITCH') {
  window.localStorage.setItem(identitySessionChangeKey, JSON.stringify({ action, nonce: crypto.randomUUID() }));
  window.localStorage.removeItem(identitySessionChangeKey);
}

export function SignOutCommand({ label }: { label: string }) {
  async function signOut() {
    clearProtectedClientState();
    announceIdentitySessionChange('SIGN_OUT');
    const response = await fetch('/api/auth/keycloak-logout', {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) throw new Error('Sign out request was denied.');
    const result: unknown = await response.json();
    if (
      !result ||
      typeof result !== 'object' ||
      !('logoutPath' in result) ||
      typeof result.logoutPath !== 'string' ||
      !result.logoutPath.startsWith('/api/auth/keycloak-logout?nonce=')
    ) {
      throw new Error('Sign out response was invalid.');
    }
    window.location.assign(result.logoutPath);
  }

  return (
    <button aria-label={label} className="account-command" type="button" onClick={() => void signOut()}>
      <LogOut aria-hidden="true" size={19} />
      <span>{label}</span>
    </button>
  );
}

export function AccountSwitchCommand({ label }: { label: string }) {
  return (
    <button
      aria-label={label}
      className="account-command"
      type="button"
      onClick={() => {
        clearProtectedClientState();
        announceIdentitySessionChange('ACCOUNT_SWITCH');
        void signIn('keycloak', { callbackUrl: '/home' }, { prompt: 'select_account' });
      }}
    >
      <RefreshCw aria-hidden="true" size={19} />
      <span>{label}</span>
    </button>
  );
}
