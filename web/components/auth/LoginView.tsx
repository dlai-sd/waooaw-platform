// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Constitutional basis: C-059 (Implementation Traceability)

import Link from 'next/link';
import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { AuthBrand } from '@/components/auth/AuthBrand';
import { ProviderCommands } from '@/components/auth/ProviderCommands';
import { getIdentitySession, listIdentityProviders } from '@/lib/api/identity';
import { authOptions } from '@/lib/auth';
import { getRequestI18n } from '@/lib/i18n-server';
import { safeReturnTarget } from '@/lib/safe-return';
import { getServerAccessToken } from '@/lib/server-auth';

export async function LoginView({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> }) {
  const { messages } = await getRequestI18n();
  const resolvedSearchParams = await searchParams;
  const returnTo = safeReturnTarget(resolvedSearchParams?.returnTo);
  const callbackUrl = `/login?returnTo=${encodeURIComponent(returnTo)}`;
  const session = await getServerSession(authOptions);
  if (session?.authenticated) {
    const accessToken = await getServerAccessToken();
    const identity = accessToken ? await getIdentitySession(accessToken) : { kind: 'unauthorized' as const };
    if (identity.kind === 'ready') redirect(returnTo);
    if (identity.kind === 'registration-required') {
      return (
        <section className="auth-view auth-entry-view">
          <AuthBrand subtitle="Welcome back." title="Log in to WAOOAW" />
          <p className="auth-switch">{messages.newToWaaoaw} <Link href={`/register?returnTo=${encodeURIComponent(returnTo)}`}>{messages.createAccount}</Link></p>
        </section>
      );
    }
  }
  const providers = await listIdentityProviders();
  return (
    <section className="auth-view auth-entry-view">
      <AuthBrand subtitle="Welcome back." title="Log in to WAOOAW" />
      <ProviderCommands callbackUrl={callbackUrl} intent="login" providers={providers} />
      <p className="auth-switch">{messages.newToWaaoaw} <Link href={`/register?returnTo=${encodeURIComponent(returnTo)}`}>{messages.createAccount}</Link></p>
    </section>
  );
}