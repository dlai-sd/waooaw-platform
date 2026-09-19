'use client';

// Implements: work-contracts/WC-092-demo-authentication-experience-repair.md §Acceptance Matrix WC092-A01-A02
// Constitutional basis: C-059 (Implementation Traceability), C-071 (Accessible interaction)

import { AuthBoundary } from './AuthBoundary';
import { AuthDialog } from './AuthDialog';
import { useAuthJourney } from './AuthJourney';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { recordAuthTransition } from '@/lib/auth-transition';

export function AuthLaunchIndicator() {
  const journey = useAuthJourney();
  const pathname = usePathname();
  useEffect(() => {
    if (journey?.launching) recordAuthTransition('ROUTE_RENDERED');
  }, [journey?.launching]);
  if (!journey?.launching || pathname === '/login' || pathname === '/register') return null;
  const intent = journey.current.destination === '/register' ? 'register' : 'login';
  return (
    <AuthDialog routeReady={false} variant="entry">
      <AuthBoundary intent={intent} />
    </AuthDialog>
  );
}
