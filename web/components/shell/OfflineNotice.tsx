'use client';

// Implements: architecture/reference/ux/hybrid-application-shell.md §Interaction and Failure Semantics
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { WifiOff } from 'lucide-react';
import { useEffect, useState } from 'react';

export function OfflineNotice() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  return offline ? (
    <div className="offline-notice" role="status">
      <WifiOff aria-hidden="true" size={18} /> You are offline. No changes will be sent.
    </div>
  ) : null;
}