// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Acquisition Runtime Boundary
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { NextResponse } from 'next/server';
import { validateAcquisitionEvent } from '@/lib/acquisition';
import { optionalConsent, parseConsentCookie } from '@/lib/consent';
import { dispatchAcquisitionEvent, type AcquisitionEvent } from '@/lib/marketing-server';
import { resolveLocale } from '@/lib/preferences';

function cookieValue(cookieHeader: string | null, name: string): string | undefined {
  return cookieHeader?.split(';').map((part) => part.trim()).find((part) => part.startsWith(`${name}=`))?.slice(name.length + 1);
}

export async function POST(request: Request) {
  let input: unknown;
  try { input = await request.json(); } catch { return NextResponse.json({ error: 'INVALID_EVENT' }, { status: 400 }); }
  const result = validateAcquisitionEvent(input);
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: 400 });
  const requestUrl = new URL(request.url);
  const referrer = request.headers.get('referer');
  let publicRoute: string;
  try {
    const referrerUrl = new URL(referrer ?? '');
    if (referrerUrl.origin !== requestUrl.origin || referrerUrl.pathname.startsWith('/api/') || referrerUrl.pathname.startsWith('/admin/')) throw new Error('invalid acquisition context');
    publicRoute = referrerUrl.pathname;
  } catch {
    return NextResponse.json({ error: 'INVALID_CONTEXT' }, { status: 400 });
  }
  const privacySignal = request.headers.get('dnt') === '1' || request.headers.get('sec-gpc') === '1';
  const cookieHeader = request.headers.get('cookie');
  const consent = optionalConsent(parseConsentCookie(cookieHeader), privacySignal);
  if (!consent.analytics && !consent.advertising && result.event.event_name !== 'consent_updated') return NextResponse.json({ error: 'CONSENT_REQUIRED' }, { status: 403 });
  const event = {
    ...result.event,
    event_id: result.event.event_id as string,
    event_name: result.event.event_name as string,
    deduplication_id: result.event.deduplication_id as string,
    timestamp: new Date().toISOString(),
    route_id: publicRoute,
    locale: resolveLocale(cookieValue(cookieHeader, 'waooaw-locale')),
    environment: process.env.WAOOAW_ENVIRONMENT === 'production' || process.env.WAOOAW_ENVIRONMENT === 'uat' ? process.env.WAOOAW_ENVIRONMENT : 'demo',
    consent,
  } satisfies AcquisitionEvent;
  await dispatchAcquisitionEvent(event);
  return new NextResponse(null, { status: 202, headers: { 'Cache-Control': 'no-store' } });
}