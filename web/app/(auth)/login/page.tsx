// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-059 (Implementation Traceability)

import { LoginView } from '@/components/auth/LoginView';
import { redirect } from 'next/navigation';

type LoginSearchParams = {
  returnTo?: string | string[];
  state?: string | string[];
};

export default async function LoginPage({ searchParams }: { searchParams?: Promise<LoginSearchParams> }) {
  const resolvedSearchParams = await searchParams;
  if (resolvedSearchParams?.state === 'waooaw-home-after-logout') redirect('/');
  if (resolvedSearchParams?.state === 'waooaw-register-after-logout:GOOGLE')
    redirect('/register?sessionReset=1&provider=GOOGLE');
  if (resolvedSearchParams?.state === 'waooaw-register-after-logout:FACEBOOK')
    redirect('/register?sessionReset=1&provider=FACEBOOK');
  return <LoginView searchParams={searchParams} />;
}
