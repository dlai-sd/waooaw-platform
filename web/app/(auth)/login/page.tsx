// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-059 (Implementation Traceability)

import { LoginView } from '@/components/auth/LoginView';

export default function LoginPage({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> }) {
	return <LoginView searchParams={searchParams} />;
}