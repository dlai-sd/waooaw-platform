// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-03
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { StateView } from '@/components/system/StateView';
export default function ForbiddenPage() { return <main className="system-page"><StateView kind="forbidden" title="Access not permitted" description="Your current role does not permit access to this area." /></main>; }