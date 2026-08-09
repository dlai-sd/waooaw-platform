'use client';

// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-05
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { useEffect, useState } from 'react';
import { globalErrorMessages } from '@/lib/global-error-messages';
import { defaultLocale, directionForLocale, resolveLocale, type SupportedLocale } from '@/lib/preferences';

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const [locale, setLocale] = useState<SupportedLocale>(defaultLocale);
  useEffect(() => {
    const localeCookie = document.cookie.split('; ').find((cookie) => cookie.startsWith('waooaw-locale='))?.split('=')[1];
    setLocale(resolveLocale(localeCookie ? decodeURIComponent(localeCookie) : undefined));
  }, []);
  const messages = globalErrorMessages[locale];
  return <html dir={directionForLocale(locale)} lang={locale}><body><main className="system-page"><section className="state-view"><h1>{messages.globalErrorTitle}</h1><p>{messages.globalErrorDescription}</p><button className="primary-command" type="button" onClick={reset}>{messages.tryAgain}</button></section></main></body></html>;
}