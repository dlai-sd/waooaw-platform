// Implements: architecture/reference/ux/hybrid-application-shell.md §Interaction and Failure Semantics
// Constitutional basis: C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
export default function NotFound() { return <main className="system-page"><StateView kind="not-found" title="Page not found" description="The requested page does not exist or is no longer available." /></main>; }