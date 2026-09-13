// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Constitutional basis: C-059 (Implementation Traceability)

import Link from 'next/link';
import { ProviderCommands } from '@/components/auth/ProviderCommands';
import { listIdentityProviders } from '@/lib/api/identity';
import { getRequestI18n } from '@/lib/i18n-server';
import { safeReturnTarget } from '@/lib/safe-return';

export async function LoginView({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> }) {
  const { messages } = await getRequestI18n();
  const resolvedSearchParams = await searchParams;
  const returnTo = safeReturnTarget(resolvedSearchParams?.returnTo);
  const callbackUrl = `/register?returnTo=${encodeURIComponent(returnTo)}`;
  const providers = await listIdentityProviders();
  return (
    <section className="auth-view auth-entry-view">
      <h1 id="auth-dialog-title">{messages.login}</h1>
      <ProviderCommands callbackUrl={callbackUrl} intent="login" providers={providers} />
      <p className="auth-switch">{messages.newToWaaoaw} <Link href={`/register?returnTo=${encodeURIComponent(returnTo)}`}>{messages.createAccount}</Link></p>
    </section>
  );
}