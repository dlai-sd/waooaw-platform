// Implements: architecture/reference/ux/wc-034-implementation-decomposition.md §F2
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { getServerSession } from 'next-auth';
import { RegistrationFlow } from '@/components/auth/RegistrationFlow';
import { SignInCommand } from '@/components/auth/SignInCommand';
import { authOptions } from '@/lib/auth';
import { getIdentityMessages } from '@/lib/identity-messages';
import { getRequestI18n } from '@/lib/i18n-server';

export default async function RegisterPage() {
	const session = await getServerSession(authOptions);
	const { locale } = getRequestI18n();
	const messages = getIdentityMessages(locale);
	return <section className="auth-view identity-view"><p className="eyebrow">{messages.eyebrow}</p><h1>{messages.title}</h1><p>{session?.authenticated ? messages.description : messages.signInDescription}</p>{session?.authenticated ? <RegistrationFlow locale={locale} messages={messages} /> : <SignInCommand callbackUrl="/register" label={messages.signInFirst} />}</section>;
}