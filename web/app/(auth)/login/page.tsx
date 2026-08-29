// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-059 (Implementation Traceability)

import Link from 'next/link';
import { AppleSignInCommand } from '@/components/auth/AppleSignInCommand';
import { SignInCommand } from '@/components/auth/SignInCommand';
import { getRequestI18n } from '@/lib/i18n-server';
import { safeReturnTarget } from '@/lib/safe-return';
export default async function LoginPage({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> }) { const { messages } = await getRequestI18n(); const resolvedSearchParams = await searchParams; return <section className="auth-view"><p className="eyebrow">{messages.secureAccess}</p><h1>{messages.welcomeBack}</h1><p>{messages.identityBrokerDescription}</p><div className="provider-commands"><SignInCommand callbackUrl={safeReturnTarget(resolvedSearchParams?.returnTo)} label={messages.signInSecurely} /><AppleSignInCommand /></div><p>{messages.newToWaaoaw} <Link href="/register">{messages.createAccount}</Link></p></section>; }