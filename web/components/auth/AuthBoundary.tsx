'use client';

import { LoaderCircle, RotateCcw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { AuthBrand } from './AuthBrand';
import { getMessages } from '@/lib/i18n';
import { resolveLocale } from '@/lib/preferences';

export function AuthBoundary({ failed = false, intent = 'login', retry }: {
  failed?: boolean;
  intent?: 'login' | 'register';
  retry?: () => void;
}) {
  const [expired, setExpired] = useState(false);
  const [locale, setLocale] = useState<ReturnType<typeof resolveLocale>>('en');
  useEffect(() => {
    setLocale(resolveLocale(document.documentElement.lang));
    const timeout = window.setTimeout(() => setExpired(true), 15_000);
    return () => window.clearTimeout(timeout);
  }, []);
  const messages = getMessages(locale);
  const unavailable = failed || expired;

  return (
    <section className="auth-view auth-boundary" aria-busy={!unavailable}>
      {unavailable
        ? <><p className="eyebrow">{messages.secureAccess}</p><h1 id="auth-dialog-title">{messages.authErrorTitle}</h1></>
        : <AuthBrand
            subtitle={intent === 'register' ? 'Start your professional journey.' : 'Welcome back.'}
            title={intent === 'register' ? 'Create your WAOOAW account' : 'Log in to WAOOAW'}
          />}
      <div role={unavailable ? 'alert' : 'status'} aria-live="polite">
        {!unavailable && <LoaderCircle className="auth-loading-icon" aria-hidden="true" size={24} />}
        <p>{unavailable ? messages.authErrorDescription : messages.loadingDescription}</p>
      </div>
      {unavailable && <button className="secondary-command" type="button" onClick={retry ?? (() => location.reload())}>
        <RotateCcw aria-hidden="true" size={18} /> {messages.tryAgain}
      </button>}
    </section>
  );
}