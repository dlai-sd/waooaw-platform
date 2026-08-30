'use client';
// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Attribution, Retention, And Failure
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { marketingConfig } from '@/config/marketing';
import { optionalConsent, parseConsentCookie } from '@/lib/consent';

type EventName = 'public_page_viewed' | 'professional_viewed' | 'registration_started' | 'hire_journey_started' | 'contact_invoked' | 'consent_updated';
type OptionalConsent = ReturnType<typeof optionalConsent>;
type SessionContext = { id: string; expiresAt: number; attribution: Record<string, string> };

const sessionKey = 'waooaw:acquisition:session';
const boundedValue = /^[\p{L}\p{N} ._/-]{1,100}$/u;
let memorySessionId: string | undefined;

function randomId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const value = [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
  return `${value.slice(0, 8)}-${value.slice(8, 12)}-${value.slice(12, 16)}-${value.slice(16, 20)}-${value.slice(20)}`;
}

function privacySignal(): boolean {
  return navigator.doNotTrack === '1' || (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl === true;
}

function readSession(consent: OptionalConsent): SessionContext {
  const now = Date.now();
  const fallback = { id: memorySessionId ??= randomId(), expiresAt: now, attribution: {} };
  if (!consent.analytics && !consent.advertising) return fallback;
  try {
    const stored = JSON.parse(sessionStorage.getItem(sessionKey) ?? '') as SessionContext;
    if (stored.expiresAt > now && /^[0-9a-f-]{36}$/i.test(stored.id)) return stored;
  } catch {
    // Invalid or expired acquisition context is replaced, never repaired with untrusted values.
  }
  const attribution = Object.fromEntries(['utm_source', 'utm_medium', 'utm_campaign'].flatMap((key) => {
    const value = new URLSearchParams(location.search).get(key);
    return value && boundedValue.test(value) ? [[key, value]] : [];
  }));
  const session = { id: randomId(), expiresAt: now + marketingConfig.attributionWindowMinutes * 60_000, attribution };
  sessionStorage.setItem(sessionKey, JSON.stringify(session));
  return session;
}

export function recordAcquisitionEvent(eventName: EventName, consent: OptionalConsent, data: Record<string, string | boolean> = {}) {
  const session = readSession(consent);
  const eventId = randomId();
  void fetch('/api/acquisition/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_id: eventId,
      event_name: eventName,
      schema_version: '1.0',
      timestamp: new Date().toISOString(),
      route_id: location.pathname,
      locale: document.documentElement.lang || 'en',
      environment: 'demo',
      consent,
      deduplication_id: session.id,
      ...session.attribution,
      ...data,
    }),
    keepalive: true,
  }).catch(() => undefined);
}

export function AcquisitionController() {
  const pathname = usePathname();
  useEffect(() => {
    const currentConsent = () => optionalConsent(parseConsentCookie(document.cookie), privacySignal());
    const consent = currentConsent();
    if (consent.analytics || consent.advertising) {
      recordAcquisitionEvent('public_page_viewed', consent);
      const professional = pathname.match(/^\/professionals\/([^/]+)$/)?.[1];
      if (professional) recordAcquisitionEvent('professional_viewed', consent, { professional_type: professional });
    }
    const onClick = (event: MouseEvent) => {
      const link = (event.target as Element | null)?.closest('a');
      if (!link) return;
      const next = currentConsent();
      if (!next.analytics && !next.advertising) return;
      if (link.href.startsWith('mailto:')) recordAcquisitionEvent('contact_invoked', next, { contact_intent: pathname.slice(1) || 'home' });
      else if (link.pathname === '/register') {
        const professional = new URL(link.href).searchParams.get('professional');
        recordAcquisitionEvent(professional ? 'hire_journey_started' : 'registration_started', next, professional
          ? { entry_route: pathname, professional_type: professional }
          : { entry_route: pathname });
      }
    };
    document.addEventListener('click', onClick);
    return () => {
      document.removeEventListener('click', onClick);
    };
  }, [pathname]);
  return null;
}