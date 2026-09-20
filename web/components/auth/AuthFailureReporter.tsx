'use client';

// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S12
// Constitutional basis: C-002, C-059, C-063

import { useEffect } from 'react';
import { recordAuthTransition } from '@/lib/auth-transition';

export function AuthFailureReporter() {
  useEffect(() => recordAuthTransition('CALLBACK_FAILED', 'BROKER_CALLBACK_FAILED'), []);
  return null;
}