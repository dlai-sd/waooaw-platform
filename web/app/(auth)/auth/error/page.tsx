// Implements: architecture/reference/ux/hybrid-application-shell.md §Interaction and Failure Semantics
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
export default function AuthErrorPage() { return <StateView actionHref="/login" actionLabel="Try secure sign in again" kind="error" title="Sign in could not be completed" description="No account or relationship change was made." />; }