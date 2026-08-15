// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-03
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default async function ForbiddenPage() { const { messages } = await getRequestI18n(); return <main className="system-page"><StateView actionLabel={messages.returnHome} kind="forbidden" title={messages.accessNotPermitted} description={messages.accessNotPermittedDescription} /></main>; }