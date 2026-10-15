// Implements: architecture/reference/ux/wc-034-implementation-decomposition.md §F2
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { RegisterView } from '@/components/auth/RegisterView';

type RegisterSearchParams = {
  provider?: string | string[];
  returnTo?: string | string[];
  sessionReset?: string | string[];
};

export default function RegisterPage({ searchParams }: { searchParams?: Promise<RegisterSearchParams> }) {
  return <RegisterView searchParams={searchParams} />;
}
