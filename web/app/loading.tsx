// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-05
// Constitutional basis: C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default function Loading() { const { messages } = getRequestI18n(); return <main className="system-page"><StateView kind="loading" title={messages.loading} description={messages.loadingDescription} /></main>; }