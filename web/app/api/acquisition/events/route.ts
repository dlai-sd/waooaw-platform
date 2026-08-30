// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Acquisition Runtime Boundary
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { NextResponse } from 'next/server';
import { validateAcquisitionEvent } from '@/lib/acquisition';
import { optionalConsent, parseConsentCookie } from '@/lib/consent';

export async function POST(request: Request) {
  let input: unknown;
  try { input = await request.json(); } catch { return NextResponse.json({ error: 'INVALID_EVENT' }, { status: 400 }); }
  const result = validateAcquisitionEvent(input);
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: 400 });
  const privacySignal = request.headers.get('dnt') === '1' || request.headers.get('sec-gpc') === '1';
  const consent = optionalConsent(parseConsentCookie(request.headers.get('cookie')), privacySignal);
  if (!consent.analytics && !consent.advertising && result.event.event_name !== 'consent_updated') return NextResponse.json({ error: 'CONSENT_REQUIRED' }, { status: 403 });
  return new NextResponse(null, { status: 202, headers: { 'Cache-Control': 'no-store' } });
}