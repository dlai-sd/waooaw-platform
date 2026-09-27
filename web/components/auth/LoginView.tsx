// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R002
// Implements: architecture/reference/ux/wc-105-authentication-flow-defect-remediation-plan.md AUTH-UI-03
// Constitutional basis: C-059 (Implementation Traceability)

import Link from 'next/link';
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
    if (identity.kind === 'forbidden' || identity.kind === 'step-up') redirect('/403');
  }
  const providers = await listIdentityProviders();
  return (
    <section className="auth-view auth-entry-view">
      <AuthBrand subtitle="Welcome back." title="Log in to WAOOAW" />
      <div aria-hidden="true" className="auth-provider-status auth-provider-status-ready" />
      <ProviderCommands callbackUrl={callbackUrl} intent="login" providers={providers} />
      <p className="auth-switch">
        Don&apos;t have an account?{' '}
        <Link href={`/register?returnTo=${encodeURIComponent(returnTo)}`}>Register</Link>
      </p>
    </section>
  );
}
