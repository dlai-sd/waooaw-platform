/** @jest-environment node */
// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Acquisition Runtime Boundary
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { POST } from './route';
import { consentCookieName, createConsentPreference } from '@/lib/consent';

const event = { event_id: '550e8400-e29b-41d4-a716-446655440000', event_name: 'public_page_viewed', schema_version: '1.0', route_id: 'home' };
const request = (headers: HeadersInit = {}, body: unknown = event) => new Request('https://waooaw.com/api/acquisition/events', { method: 'POST', headers: { 'content-type': 'application/json', ...headers }, body: JSON.stringify(body) });

describe('acquisition route consent enforcement', () => {
  it('does not trust an arbitrary consent header', async () => expect((await POST(request({ 'x-waooaw-consent': 'analytics=true' }))).status).toBe(403));
  it('accepts an event with a current first-party category preference', async () => {
    const cookie = `${consentCookieName}=${encodeURIComponent(JSON.stringify(createConsentPreference(true, false)))}`;
    expect((await POST(request({ cookie }))).status).toBe(202);
  });
  it.each(['dnt', 'sec-gpc'])('honors browser privacy signal %s', async (header) => {
    const cookie = `${consentCookieName}=${encodeURIComponent(JSON.stringify(createConsentPreference(true, true)))}`;
    expect((await POST(request({ cookie, [header]: '1' }))).status).toBe(403);
  });
});