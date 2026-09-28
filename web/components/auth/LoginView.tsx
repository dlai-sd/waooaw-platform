// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R002
// Implements: work-contracts/WC-107-requirements.yaml WC107-R001, WC107-R008
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
  let recovery: { code: string; correlationId?: string } | undefined;
  if (accessToken) {
    const identity = await getIdentitySession(accessToken);
    if (identity.kind === 'ready') redirect(returnTo);
    if (identity.kind === 'registration-required') redirect('/marketplace');
    if (identity.kind === 'forbidden') recovery = { code: identity.code, correlationId: identity.correlationId };
    if (identity.kind === 'step-up') {
      recovery = { code: 'IDENTITY_STEP_UP_REQUIRED', correlationId: identity.correlationId };
    }
  }
  const providers = await listIdentityProviders();
  return (
    <section className="auth-view auth-entry-view">
      <AuthBrand
        subtitle={recovery ? 'Sign in again to continue safely.' : 'Welcome back.'}
        title="Log in to WAOOAW"
      />
      {recovery ? (
        <div className="identity-status" data-reason-code={recovery.code} role="alert">
          <p>We couldn&apos;t continue with the current session. Choose your account and try again.</p>
          {recovery.correlationId ? <span>Reference: {recovery.correlationId}</span> : null}
        </div>
      ) : null}
      <div aria-hidden="true" className="auth-provider-status auth-provider-status-ready" />
      <ProviderCommands callbackUrl={callbackUrl} intent="login" providers={providers} />
      <p className="auth-switch">
        Don&apos;t have an account? <Link href={`/register?returnTo=${encodeURIComponent(returnTo)}`}>Register</Link>
      </p>
    </section>
  );
}
