// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import type { ReactNode } from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { authOptions } from '@/lib/auth';

export default async function CustomerLayout({ children }: { children: ReactNode }) {
  const session = await getServerSession(authOptions);
  if (!session?.accessToken) redirect('/login');
  return <AppShell variant="customer">{children}</AppShell>;
}