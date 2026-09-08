// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import type { ReactNode } from 'react';
import { ProtectedAppShell } from '@/components/shell/ProtectedAppShell';
import { StateView } from '@/components/system/StateView';
import { authOptions } from '@/lib/auth';
import { getIdentitySession } from '@/lib/api/identity';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function CustomerLayout({ children }: { children: ReactNode }) {
  const session = await getServerSession(authOptions);
  if (!session?.authenticated) redirect('/login');
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/login');
  const identity = await getIdentitySession(accessToken);
  if (identity.kind === 'expired' || identity.kind === 'unauthorized') redirect('/login');
  const { locale, messages } = await getRequestI18n();
  if (identity.kind === 'step-up') {
    return <ProtectedAppShell locale={locale} messages={messages} variant="customer"><StateView actionHref="/login" actionLabel={messages.retrySecureSignIn} kind="forbidden" title={messages.accessNotPermitted} description={messages.accessNotPermittedDescription} /></ProtectedAppShell>;
  }
  if (identity.kind === 'unavailable') {
    return <ProtectedAppShell locale={locale} messages={messages} variant="customer"><StateView actionHref="/home" actionLabel={messages.tryAgain} kind="error" title={messages.globalErrorTitle} description={messages.globalErrorDescription} /></ProtectedAppShell>;
  }
  return <ProtectedAppShell identitySession={identity.session} locale={locale} messages={messages} variant="customer">{children}</ProtectedAppShell>;
}