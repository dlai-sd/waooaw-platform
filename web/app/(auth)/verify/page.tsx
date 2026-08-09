// Implements: architecture/reference/ux/wc-034-implementation-decomposition.md §F2
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { getServerSession } from 'next-auth';
import { MobileVerificationFlow } from '@/components/auth/MobileVerificationFlow';
import { SignInCommand } from '@/components/auth/SignInCommand';
import { authOptions } from '@/lib/auth';
import { getIdentityMessages } from '@/lib/identity-messages';
import { getRequestI18n } from '@/lib/i18n-server';
import { safeReturnTarget } from '@/lib/safe-return';

export default async function VerifyPage({ searchParams }: { searchParams?: { returnTo?: string | string[] } }) {
	const session = await getServerSession(authOptions);
	const { locale } = getRequestI18n();
	const messages = getIdentityMessages(locale);
	const returnTo = safeReturnTarget(searchParams?.returnTo);
	return <section className="auth-view identity-view"><p className="eyebrow">{messages.eyebrow}</p><h1>{messages.optionalMobile}</h1><p>{messages.description}</p>{session?.authenticated ? <MobileVerificationFlow messages={messages} returnTo={returnTo} /> : <SignInCommand callbackUrl="/verify" label={messages.signInFirst} />}</section>;
}