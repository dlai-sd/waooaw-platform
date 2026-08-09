// Implements: architecture/reference/ux/hybrid-application-shell.md §Interaction and Failure Semantics
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default function AuthErrorPage() { const { messages } = getRequestI18n(); return <StateView actionHref="/login" actionLabel={messages.retrySecureSignIn} kind="error" title={messages.authErrorTitle} description={messages.authErrorDescription} />; }