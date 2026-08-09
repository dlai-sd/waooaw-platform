// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default function BlogsPage() { const { messages } = getRequestI18n(); return <StateView actionLabel={messages.returnHome} kind="empty" title={messages.blogs} description={messages.insightsDescription} />; }