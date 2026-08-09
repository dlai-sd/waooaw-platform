'use client';

// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-059 (Implementation Traceability)

import { ArrowRight } from 'lucide-react';
import { signIn } from 'next-auth/react';
import { useState } from 'react';

export function SignInCommand({ label }: { label: string }) {
  const [pending, setPending] = useState(false);
  return <button className="primary-command" disabled={pending} type="button" onClick={() => { setPending(true); void signIn('keycloak', { callbackUrl: '/home' }); }}>{label} <ArrowRight aria-hidden="true" size={18} /></button>;
}