// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { getServerSession } from 'next-auth';
import { ProviderCommands } from '@/components/auth/ProviderCommands';
import { RegistrationFlow } from '@/components/auth/RegistrationFlow';
import { listIdentityProviders } from '@/lib/api/identity';
import { authOptions } from '@/lib/auth';
import { getIdentityMessages } from '@/lib/identity-messages';
import { getRequestI18n } from '@/lib/i18n-server';

export async function RegisterView() {
  const session = await getServerSession(authOptions);
  const { locale } = await getRequestI18n();
  const messages = getIdentityMessages(locale);
  const providers = session?.authenticated ? [] : await listIdentityProviders();
  return (
    <section className="auth-view identity-view">
      <p className="eyebrow">{messages.eyebrow}</p>
      <h1 id="auth-dialog-title">{messages.title}</h1>
      <p>{session?.authenticated ? messages.description : messages.signInDescription}</p>
      {session?.authenticated
        ? <RegistrationFlow locale={locale} messages={messages} />
        : <ProviderCommands callbackUrl="/register" providers={providers} />}
    </section>
  );
}