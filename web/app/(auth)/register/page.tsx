// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
export default function RegisterPage() { return <StateView actionHref="/login" actionLabel="Continue to secure sign in" kind="empty" title="Registration is not available yet" description="F1 provides the authentication shell only. Registration begins after its identity contracts are approved." />; }