'use client';

import { signOut } from 'next-auth/react';
import { useEffect, useRef } from 'react';
import { identitySessionChangeKey } from './SignOutCommand';

export function SessionValidityGuard() {
  const validating = useRef(false);

  useEffect(() => {
    async function clearRevokedSession() {
      if (validating.current) return;
      validating.current = true;
      try {
        const response = await fetch('/api/identity/sessions', {
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        });
        if (response.status === 401 || response.status === 403) {
          await signOut({ callbackUrl: '/login' });
        }
      } finally {
        validating.current = false;
      }
    }

    function handleFocus() {
      if (document.visibilityState === 'visible') void clearRevokedSession();
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') void clearRevokedSession();
    }

    function handleStorage(event: StorageEvent) {
      if (event.key === identitySessionChangeKey && event.newValue) void signOut({ callbackUrl: '/login' });
    }

    window.addEventListener('focus', handleFocus);
    window.addEventListener('storage', handleStorage);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('storage', handleStorage);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  return null;
}