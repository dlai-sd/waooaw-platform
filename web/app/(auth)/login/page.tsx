// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-059 (Implementation Traceability)

import Link from 'next/link';
import { SignInCommand } from '@/components/auth/SignInCommand';
import { getRequestI18n } from '@/lib/i18n-server';
import { safeReturnTarget } from '@/lib/safe-return';
export default function LoginPage({ searchParams }: { searchParams?: { returnTo?: string | string[] } }) { const { messages } = getRequestI18n(); return <section className="auth-view"><p className="eyebrow">{messages.secureAccess}</p><h1>{messages.welcomeBack}</h1><p>{messages.identityBrokerDescription}</p><SignInCommand callbackUrl={safeReturnTarget(searchParams?.returnTo)} label={messages.signInSecurely} /><p>{messages.newToWaaoaw} <Link href="/register">{messages.createAccount}</Link></p></section>; }