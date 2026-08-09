// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
export default function VerifyPage() { return <StateView actionHref="/login" actionLabel="Return to login" kind="empty" title="Verification is not active" description="Verification behavior belongs to F2 and is unavailable in the F1 shell." />; }