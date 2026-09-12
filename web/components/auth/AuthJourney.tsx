'use client';

import { useRouter } from 'next/navigation';
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { safePublicReturnTarget } from '@/lib/safe-return';

type Journey = { origin: string; trigger: HTMLElement | null };
type AuthJourneyState = {
  current: Journey;
  launching: boolean;
  cancelLaunch: () => void;
  completeLaunch: () => void;
};
const AuthJourneyContext = createContext<AuthJourneyState | null>(null);

export function AuthJourney({ children }: { children: ReactNode }) {
  const journey = useRef<Journey>({ origin: '/', trigger: null });
  const router = useRouter();
  const [launching, setLaunching] = useState(false);
  const cancelLaunch = useCallback(() => setLaunching(false), []);
  const completeLaunch = useCallback(() => setLaunching(false), []);

  useEffect(() => {
    function capture(event: MouseEvent) {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const link = event.target instanceof Element ? event.target.closest('a') : null;
      if (!link || link.target === '_blank' || link.origin !== location.origin) return;
      if (!['/login', '/register'].includes(link.pathname) || ['/login', '/register'].includes(location.pathname)) return;
      event.preventDefault();
      journey.current = {
        origin: safePublicReturnTarget(location.pathname + location.hash),
        trigger: link,
      };
      setLaunching(true);
      router.push(link.pathname + link.search + link.hash, { scroll: false });
    }
    document.addEventListener('click', capture, true);
    return () => document.removeEventListener('click', capture, true);
  }, [router]);

  return <AuthJourneyContext.Provider value={{
    current: journey.current,
    launching,
    cancelLaunch,
    completeLaunch,
  }}>{children}</AuthJourneyContext.Provider>;
}

export function useAuthJourney() {
  return useContext(AuthJourneyContext);
}