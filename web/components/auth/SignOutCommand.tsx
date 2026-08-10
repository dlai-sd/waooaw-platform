'use client';

// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { LogOut, RefreshCw } from 'lucide-react';
import { signIn, signOut } from 'next-auth/react';

export function clearProtectedClientState(storages: readonly Storage[] = [window.sessionStorage, window.localStorage]) {
  for (const storage of storages) {
    for (let index = storage.length - 1; index >= 0; index -= 1) {
      const key = storage.key(index);
      if (key?.startsWith('waooaw:')) storage.removeItem(key);
    }
  }
}

export function SignOutCommand({ label }: { label: string }) {
  return <button aria-label={label} className="icon-command" title={label} type="button" onClick={() => { clearProtectedClientState(); void signOut({ callbackUrl: '/' }); }}><LogOut aria-hidden="true" size={19} /></button>;
}

export function AccountSwitchCommand({ label }: { label: string }) {
  return <button aria-label={label} className="icon-command" title={label} type="button" onClick={() => { clearProtectedClientState(); void signIn('keycloak', { callbackUrl: '/home' }, { prompt: 'select_account' }); }}><RefreshCw aria-hidden="true" size={19} /></button>;
}