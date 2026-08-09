// Implements: architecture/reference/components/identity-boundary.md §6.3 WhatsApp-to-web linking
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { getServerSession } from 'next-auth';
import { SignInCommand } from '@/components/auth/SignInCommand';
import { StateView } from '@/components/system/StateView';
import { authOptions } from '@/lib/auth';
import { getIdentityMessages } from '@/lib/identity-messages';
import { getRequestI18n } from '@/lib/i18n-server';

export default async function AccountLinkPage() {
  const session = await getServerSession(authOptions);
  const { locale } = getRequestI18n();
  const messages = getIdentityMessages(locale);
  if (!session?.authenticated) return <section className="auth-view"><h1>{messages.duplicate}</h1><SignInCommand callbackUrl="/account-link" label={messages.signInFirst} /></section>;
  return <StateView actionHref="/home" actionLabel={messages.retry} kind="empty" title={messages.duplicate} description="Continue from the verified WhatsApp conversation. No link will be created until the internal channel proof and fresh account assurance are both available." />;
}