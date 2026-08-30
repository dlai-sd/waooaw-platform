/** @jest-environment node */
// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Acquisition Runtime Boundary
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { POST } from './route';
import { consentCookieName, createConsentPreference } from '@/lib/consent';
import { dispatchAcquisitionEvent } from '@/lib/marketing-server';

jest.mock('@/lib/marketing-server', () => ({ dispatchAcquisitionEvent: jest.fn().mockResolvedValue([]) }));
const dispatch = jest.mocked(dispatchAcquisitionEvent);

const event = { event_id: '550e8400-e29b-41d4-a716-446655440000', event_name: 'public_page_viewed', schema_version: '1.0', timestamp: '2026-08-30T00:00:00.000Z', route_id: '/forged', locale: 'ur', environment: 'production', consent: { analytics: true, advertising: true }, deduplication_id: '550e8400-e29b-41d4-a716-446655440001' };
const request = (headers: HeadersInit = {}, body: unknown = event) => new Request('https://waooaw.com/api/acquisition/events', { method: 'POST', headers: { 'content-type': 'application/json', referer: 'https://waooaw.com/', ...headers }, body: JSON.stringify(body) });

describe('acquisition route consent enforcement', () => {
  beforeEach(() => dispatch.mockClear());
  it('does not trust an arbitrary consent header', async () => expect((await POST(request({ 'x-waooaw-consent': 'analytics=true' }))).status).toBe(403));
  it('accepts an event with a current first-party category preference', async () => {
    const cookie = `${consentCookieName}=${encodeURIComponent(JSON.stringify(createConsentPreference(true, false)))}`;
    expect((await POST(request({ cookie }))).status).toBe(202);
    expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ route_id: '/', locale: 'en', environment: 'demo', consent: { analytics: true, advertising: false } }));
    expect(dispatch.mock.calls[0][0].timestamp).not.toBe(event.timestamp);
  });
  it('rejects missing and cross-origin public context', async () => {
    expect((await POST(request({ referer: '' }))).status).toBe(400);
    expect((await POST(request({ referer: 'https://example.com/' }))).status).toBe(400);
  });
  it.each(['dnt', 'sec-gpc'])('honors browser privacy signal %s', async (header) => {
    const cookie = `${consentCookieName}=${encodeURIComponent(JSON.stringify(createConsentPreference(true, true)))}`;
    expect((await POST(request({ cookie, [header]: '1' }))).status).toBe(403);
  });
});