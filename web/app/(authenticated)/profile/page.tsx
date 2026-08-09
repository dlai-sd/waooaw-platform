// Implements: architecture/reference/ux/hybrid-application-shell.md §Navigation Contract
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default function ProfilePage() { const { messages } = getRequestI18n(); return <StateView actionLabel={messages.returnHome} kind="empty" title={messages.profile} description={messages.profileUnavailableDescription} />; }