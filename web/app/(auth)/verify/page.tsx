// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default function VerifyPage() { const { messages } = getRequestI18n(); return <StateView actionHref="/login" actionLabel={messages.returnToLogin} kind="empty" title={messages.verificationInactive} description={messages.verificationDescription} />; }