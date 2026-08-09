// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default function RegisterPage() { const { messages } = getRequestI18n(); return <StateView actionHref="/login" actionLabel={messages.continueSecureSignIn} kind="empty" title={messages.registrationUnavailable} description={messages.registrationDescription} />; }