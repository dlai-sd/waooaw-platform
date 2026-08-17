// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-059 (Implementation Traceability), C-065 (Separation of Duties)

import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import type { ReactNode } from 'react';
import { ProtectedAppShell } from '@/components/shell/ProtectedAppShell';
import { authOptions } from '@/lib/auth';
import { getRequestI18n } from '@/lib/i18n-server';

export default async function FounderLayout({ children }: { children: ReactNode }) {
  const session = await getServerSession(authOptions);
  if (!session?.authenticated) redirect('/login');
  if (!session.founder) redirect('/403');
  const { messages } = await getRequestI18n();
  return <ProtectedAppShell messages={messages} variant="founder">{children}</ProtectedAppShell>;
}