'use client';

// Implements: architecture/reference/components/identity-boundary.md §4.1
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { SessionProvider } from 'next-auth/react';
import type { ReactNode } from 'react';

export function AuthSessionProvider({ children }: { children: ReactNode }) {
  return <SessionProvider refetchInterval={5 * 60}>{children}</SessionProvider>;
}
