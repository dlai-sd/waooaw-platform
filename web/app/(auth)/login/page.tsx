// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-059 (Implementation Traceability)

import Link from 'next/link';
import { SignInCommand } from '@/components/auth/SignInCommand';
export default function LoginPage() { return <section className="auth-view"><p className="eyebrow">Secure access</p><h1>Welcome back</h1><p>Continue through WAOOAW&apos;s approved identity broker.</p><SignInCommand /><p>New to WAOOAW? <Link href="/register">Create an account</Link></p></section>; }