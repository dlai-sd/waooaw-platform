// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R002
// Constitutional basis: C-059 (Implementation Traceability)

import { redirect } from 'next/navigation';
import { AuthBrand } from '@/components/auth/AuthBrand';
import { ProviderCommands } from '@/components/auth/ProviderCommands';
import { getIdentitySession, listIdentityProviders } from '@/lib/api/identity';
import { safeReturnTarget } from '@/lib/safe-return';
import { getServerAccessToken } from '@/lib/server-auth';

export async function LoginView({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> }) {
  const resolvedSearchParams = await searchParams;
  const returnTo = safeReturnTarget(resolvedSearchParams?.returnTo);
  const callbackUrl = `/login?returnTo=${encodeURIComponent(returnTo)}`;
  const accessToken = await getServerAccessToken();
  if (accessToken) {
    const identity = await getIdentitySession(accessToken);
    if (identity.kind === 'ready') redirect(returnTo);
    if (identity.kind === 'registration-required') redirect(`/register?returnTo=${encodeURIComponent(returnTo)}`);
    if (identity.kind === 'unavailable') redirect(returnTo);
  }
  const providers = await listIdentityProviders();
  return (
    <section className="auth-view auth-entry-view">
      <AuthBrand subtitle="Welcome back." title="Log in to WAOOAW" />
      <ProviderCommands callbackUrl={callbackUrl} intent="login" providers={providers} />
    </section>
  );
}
