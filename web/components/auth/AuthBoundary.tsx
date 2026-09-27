'use client';

// Implements: architecture/reference/ux/wc-105-authentication-flow-defect-remediation-plan.md AUTH-UI-02, AUTH-UI-03
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { RotateCcw } from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AuthBrand } from './AuthBrand';
import { pendingIdentityProviders, ProviderCommands } from './ProviderCommands';
import { getMessages } from '@/lib/i18n';
import { getIdentityMessages } from '@/lib/identity-messages';
import { resolveLocale } from '@/lib/preferences';
import { safeReturnTarget } from '@/lib/safe-return';

export function AuthBoundary({
  failed = false,
  intent = 'login',
  retry,
}: {
  failed?: boolean;
  intent?: 'login' | 'register';
  retry?: () => void;
}) {
  const [locale, setLocale] = useState<ReturnType<typeof resolveLocale>>('en');
  const searchParams = useSearchParams();
  useEffect(() => {
    setLocale(resolveLocale(document.documentElement.lang));
  }, []);
  const messages = getMessages(locale);
  const identityMessages = getIdentityMessages(locale);
  const unavailable = failed;
  const returnTo = safeReturnTarget(searchParams.get('returnTo') ?? undefined);
  const destination = intent === 'register' ? '/register' : '/login';

  return (
    <section className="auth-view auth-entry-view auth-boundary" aria-busy={!unavailable}>
      {unavailable ? (
        <>
          <p className="eyebrow">{messages.secureAccess}</p>
          <h1 id="auth-dialog-title">{messages.authErrorTitle}</h1>
        </>
      ) : (
        <AuthBrand
          subtitle={intent === 'register' ? 'Start your professional journey.' : 'Welcome back.'}
          title={intent === 'register' ? 'Create your WAOOAW account' : 'Log in to WAOOAW'}
        />
      )}
      <div
        className={unavailable ? undefined : 'auth-provider-status'}
        role={unavailable ? 'alert' : 'status'}
        aria-live="polite"
      >
        {!unavailable && <span className="auth-loading-bar" aria-hidden="true" />}
        <p>{unavailable ? messages.authErrorDescription : 'Loading secure sign-in options.'}</p>
      </div>
      {!unavailable ? (
        <ProviderCommands
          callbackUrl={`${destination}?returnTo=${encodeURIComponent(returnTo)}`}
          intent={intent}
          providers={pendingIdentityProviders}
          readinessPending
        />
      ) : null}
      {!unavailable && intent === 'login' ? (
        <p className="auth-switch">
          Don&apos;t have an account?{' '}
          <Link href={`/register?returnTo=${encodeURIComponent(returnTo)}`}>Register</Link>
        </p>
      ) : null}
      {!unavailable && intent === 'register' ? (
        <>
          <p className="auth-legal">
            {identityMessages.legalPrefix} <Link href="/terms">{identityMessages.terms}</Link>{' '}
            {identityMessages.legalAnd} <Link href="/privacy">{identityMessages.privacy}</Link>.
          </p>
          <p className="auth-switch">
            {identityMessages.existingAccount}{' '}
            <Link href={`/login?returnTo=${encodeURIComponent(returnTo)}`}>{identityMessages.signIn}</Link>
          </p>
        </>
      ) : null}
      {unavailable && (
        <button className="secondary-command" type="button" onClick={retry ?? (() => location.reload())}>
          <RotateCcw aria-hidden="true" size={18} /> {messages.tryAgain}
        </button>
      )}
    </section>
  );
}
