'use client';

import { createContext, useContext, useEffect, useRef, type ReactNode } from 'react';
import { safePublicReturnTarget } from '@/lib/safe-return';

type Journey = { origin: string; trigger: HTMLElement | null };
const AuthJourneyContext = createContext<{ current: Journey } | null>(null);

export function AuthJourney({ children }: { children: ReactNode }) {
  const journey = useRef<Journey>({ origin: '/', trigger: null });

  useEffect(() => {
    function capture(event: MouseEvent) {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const link = event.target instanceof Element ? event.target.closest('a') : null;
      if (!link || link.target === '_blank' || link.origin !== location.origin) return;
      if (!['/login', '/register'].includes(link.pathname) || ['/login', '/register'].includes(location.pathname)) return;
      journey.current = {
        origin: safePublicReturnTarget(location.pathname + location.hash),
        trigger: link,
      };
    }
    document.addEventListener('click', capture, true);
    return () => document.removeEventListener('click', capture, true);
  }, []);

  return <AuthJourneyContext.Provider value={journey}>{children}</AuthJourneyContext.Provider>;
}

export function useAuthJourney() {
  return useContext(AuthJourneyContext);
}