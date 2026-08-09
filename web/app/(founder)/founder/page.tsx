// Implements: architecture/reference/ux/wc-034-implementation-decomposition.md §F1 — Experience Foundation
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
export default function FounderHomePage() { const { messages } = getRequestI18n(); return <StateView actionLabel={messages.returnHome} kind="empty" title={messages.founderAdministration} description={messages.founderDescription} />; }