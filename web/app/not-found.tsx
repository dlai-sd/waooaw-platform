// Implements: architecture/reference/ux/hybrid-application-shell.md §Interaction and Failure Semantics
// Constitutional basis: C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default function NotFound() { const { messages } = getRequestI18n(); return <main className="system-page"><StateView actionLabel={messages.returnHome} kind="not-found" title={messages.pageNotFound} description={messages.pageNotFoundDescription} /></main>; }