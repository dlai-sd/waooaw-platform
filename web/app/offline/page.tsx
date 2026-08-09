// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-02
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default function OfflinePage() { const { messages } = getRequestI18n(); return <main className="system-page"><StateView actionLabel={messages.returnHome} kind="error" title={messages.offline} description={messages.offlineDescription} /></main>; }