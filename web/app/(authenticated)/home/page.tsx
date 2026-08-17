// Implements: architecture/reference/ux/hybrid-application-shell.md §Entry and Resume Behavior
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default async function CustomerHomePage() { const { messages } = await getRequestI18n(); return <StateView actionLabel={messages.returnHome} kind="empty" title={messages.workspaceReady} description={messages.workspaceReadyDescription} />; }