// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PWA-02
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
export default function OfflinePage() { return <main className="system-page"><StateView kind="error" title="You are offline" description="The static shell is available, but protected information and changes require a connection." /></main>; }