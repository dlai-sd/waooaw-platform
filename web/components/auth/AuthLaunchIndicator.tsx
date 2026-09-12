'use client';

// Implements: work-contracts/WC-092-demo-authentication-experience-repair.md §Acceptance Matrix WC092-A01-A02
// Constitutional basis: C-059 (Implementation Traceability), C-071 (Accessible interaction)

import { AuthBoundary } from './AuthBoundary';
import { AuthDialog } from './AuthDialog';
import { useAuthJourney } from './AuthJourney';
import { usePathname } from 'next/navigation';

export function AuthLaunchIndicator() {
  const journey = useAuthJourney();
  const pathname = usePathname();
  if (!journey?.launching || pathname === '/login' || pathname === '/register') return null;
  return <AuthDialog routeReady={false}><AuthBoundary /></AuthDialog>;
}