// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-05
// Constitutional basis: C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
export default function Loading() { return <main className="system-page"><StateView kind="loading" title="Loading" description="Preparing the requested view." /></main>; }