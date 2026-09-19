// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import Link from 'next/link';
import { AuthBrand } from '@/components/auth/AuthBrand';
import { ProviderCommands } from '@/components/auth/ProviderCommands';
import { RegistrationFlow } from '@/components/auth/RegistrationFlow';
import { listIdentityProviders } from '@/lib/api/identity';
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
  const providers = accessToken ? [] : await listIdentityProviders();
  if (!accessToken) {
    return (
      <section className="auth-view auth-entry-view identity-view">
        <AuthBrand subtitle="Start your professional journey." title="Create your WAOOAW account" />
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
  return (
    <section className="auth-view identity-view">
      <RegistrationFlow locale={locale} messages={messages} returnTo={returnTo} />
    </section>
  );
}
