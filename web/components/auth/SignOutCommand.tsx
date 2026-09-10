'use client';

// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { LogOut, RefreshCw } from 'lucide-react';
import { signIn, signOut } from 'next-auth/react';

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
}

export function SignOutCommand({ label }: { label: string }) {
  return <button aria-label={label} className="icon-command" title={label} type="button" onClick={() => { clearProtectedClientState(); announceIdentitySessionChange('SIGN_OUT'); void signOut({ callbackUrl: '/' }); }}><LogOut aria-hidden="true" size={19} /></button>;
}

export function AccountSwitchCommand({ label }: { label: string }) {
  return <button aria-label={label} className="icon-command" title={label} type="button" onClick={() => { clearProtectedClientState(); announceIdentitySessionChange('ACCOUNT_SWITCH'); void signIn('keycloak', { callbackUrl: '/home' }, { prompt: 'select_account' }); }}><RefreshCw aria-hidden="true" size={19} /></button>;
}