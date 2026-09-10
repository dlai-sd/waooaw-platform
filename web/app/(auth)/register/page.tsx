// Implements: architecture/reference/ux/wc-034-implementation-decomposition.md §F2
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { RegisterView } from '@/components/auth/RegisterView';

export default function RegisterPage({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> }) {
	return <RegisterView searchParams={searchParams} />;
}