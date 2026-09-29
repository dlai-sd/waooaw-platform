// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Implements: work-contracts/WC-107-requirements.yaml WC107-R002, WC107-R006, WC107-R008
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import Link from 'next/link';
import { redirect } from 'next/navigation';
import { AuthBrand } from '@/components/auth/AuthBrand';
import { ProviderCommands } from '@/components/auth/ProviderCommands';
import { RegistrationFlow } from '@/components/auth/RegistrationFlow';
import { getIdentitySession, listIdentityProviders } from '@/lib/api/identity';
import { getIdentityMessages } from '@/lib/identity-messages';
import { getRequestI18n } from '@/lib/i18n-server';
import { safeReturnTarget } from '@/lib/safe-return';
import { getServerAccessToken } from '@/lib/server-auth';

export async function RegisterView({
  searchParams,
}: { searchParams?: Promise<{ returnTo?: string | string[] }> } = {}) {
  const accessToken = await getServerAccessToken();
  const resolvedSearchParams = await searchParams;
  const { locale } = await getRequestI18n();
  const messages = getIdentityMessages(locale);
  const returnTo = safeReturnTarget(resolvedSearchParams?.returnTo);
  if (accessToken) {
    const identity = await getIdentitySession(accessToken);
    if (identity.kind === 'ready') redirect(returnTo);
    if (identity.kind === 'registration-required') {
      return (
        <section className="auth-view identity-view">
          <RegistrationFlow locale={locale} messages={messages} returnTo={returnTo} />
        </section>
      );
    }
    if (identity.kind === 'forbidden' || identity.kind === 'step-up') {
      redirect(`/login?returnTo=${encodeURIComponent(returnTo)}`);
    }
  }
  const providers = await listIdentityProviders();
  return (
    <section className="auth-view auth-entry-view identity-view">
      <AuthBrand subtitle="Start your professional journey." title="Create your WAOOAW account" />
      <div aria-hidden="true" className="auth-provider-status auth-provider-status-ready" />
      <ProviderCommands
        callbackUrl={`/register?returnTo=${encodeURIComponent(returnTo)}`}
        intent="register"
        providers={providers}
      />
      <p className="auth-legal">
        {messages.legalPrefix} <Link href="/terms">{messages.terms}</Link> {messages.legalAnd}{' '}
        <Link href="/privacy">{messages.privacy}</Link>.
      </p>
      <p className="auth-switch">
        {messages.existingAccount}{' '}
        <Link href={`/login?returnTo=${encodeURIComponent(returnTo)}`}>{messages.signIn}</Link>
      </p>
    </section>
  );
}
