// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import Link from 'next/link';
import { getServerSession } from 'next-auth';
import { ProviderCommands } from '@/components/auth/ProviderCommands';
import { RegistrationFlow } from '@/components/auth/RegistrationFlow';
import { listIdentityProviders } from '@/lib/api/identity';
import { authOptions } from '@/lib/auth';
import { getIdentityMessages } from '@/lib/identity-messages';
import { getRequestI18n } from '@/lib/i18n-server';
import { safeReturnTarget } from '@/lib/safe-return';

export async function RegisterView({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> } = {}) {
  const session = await getServerSession(authOptions);
  const resolvedSearchParams = await searchParams;
  const { locale } = await getRequestI18n();
  const messages = getIdentityMessages(locale);
  const returnTo = safeReturnTarget(resolvedSearchParams?.returnTo);
  const providers = session?.authenticated ? [] : await listIdentityProviders();
  if (!session?.authenticated) {
    return (
      <section className="auth-view auth-entry-view identity-view">
        <h1 id="auth-dialog-title">{messages.title}</h1>
        <ProviderCommands callbackUrl={`/register?returnTo=${encodeURIComponent(returnTo)}`} intent="register" providers={providers} />
        <p className="auth-legal">
          {messages.legalPrefix} <Link href="/terms">{messages.terms}</Link> {messages.legalAnd}{' '}
          <Link href="/privacy">{messages.privacy}</Link>.
        </p>
        <p className="auth-switch">{messages.existingAccount} <Link href={`/login?returnTo=${encodeURIComponent(returnTo)}`}>{messages.signIn}</Link></p>
      </section>
    );
  }
  return (
    <section className="auth-view identity-view">
      <p className="eyebrow">{messages.eyebrow}</p>
      <h1 id="auth-dialog-title">{messages.title}</h1>
      <p>{messages.description}</p>
      <RegistrationFlow locale={locale} messages={messages} returnTo={returnTo} />
    </section>
  );
}