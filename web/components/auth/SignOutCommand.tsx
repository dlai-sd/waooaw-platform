'use client';

// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-04
// Implements: work-contracts/WC-119-auth-session-account-switch-recovery.md WC119-R002, WC119-R005
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { beginAuthTransition, recordAuthTransition } from '@/lib/auth-transition';
import { requestKeycloakLogout } from '@/lib/keycloak-logout';
import { LogOut, RefreshCw } from 'lucide-react';
import { signOut as nextAuthSignOut } from 'next-auth/react';
import { useState } from 'react';

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

export function SignOutCommand({
  label,
  navigate = (path) => window.location.assign(path),
}: {
  label: string;
  navigate?: (path: string) => void;
}) {
  const [signingOut, setSigningOut] = useState(false);
  const [signOutFailed, setSignOutFailed] = useState(false);

  async function signOut() {
    setSigningOut(true);
    setSignOutFailed(false);
    clearProtectedClientState();
    announceIdentitySessionChange('SIGN_OUT');
    try {
      navigate(await requestKeycloakLogout());
    } catch {
      try {
        await nextAuthSignOut({ callbackUrl: '/' });
      } catch {
        setSigningOut(false);
        setSignOutFailed(true);
      }
    }
  }

  return (
    <>
      <button
        aria-label={label}
        className="account-command"
        disabled={signingOut}
        type="button"
        onClick={() => void signOut()}
      >
        <LogOut aria-hidden="true" size={19} />
        <span>{signingOut ? 'Signing out...' : label}</span>
      </button>
      {signOutFailed ? <p role="alert">Sign out could not complete. Try again.</p> : null}
    </>
  );
}

export function AccountSwitchCommand({
  label,
  navigate = (path) => window.location.assign(path),
}: {
  label: string;
  navigate?: (path: string) => void;
}) {
  const [switching, setSwitching] = useState(false);
  const [switchFailed, setSwitchFailed] = useState(false);

  async function switchAccount() {
    setSwitching(true);
    setSwitchFailed(false);
    clearProtectedClientState();
    announceIdentitySessionChange('ACCOUNT_SWITCH');
    beginAuthTransition();
    recordAuthTransition('ACCOUNT_SWITCH_REQUESTED', 'CUSTOMER_REQUESTED', 'UNKNOWN');
    try {
      navigate(await requestKeycloakLogout());
    } catch {
      recordAuthTransition('ACCOUNT_SWITCH_FAILED', 'SESSION_REVOCATION_UNCONFIRMED', 'UNKNOWN');
      setSwitching(false);
      setSwitchFailed(true);
    }
  }

  return (
    <>
      <button
        aria-label={label}
        className="account-command"
        disabled={switching}
        type="button"
        onClick={() => void switchAccount()}
      >
        <RefreshCw aria-hidden="true" size={19} />
        <span>{label}</span>
      </button>
      {switchFailed ? <p role="alert">Account switch could not start. Try again.</p> : null}
    </>
  );
}
