/** @jest-environment node */
// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Destination And Environment Matrix
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { dispatchAcquisitionEvent } from './marketing-server';

const event = {
  event_id: '550e8400-e29b-41d4-a716-446655440000',
  event_name: 'public_page_viewed',
  timestamp: '2026-08-30T00:00:00.000Z',
  deduplication_id: '550e8400-e29b-41d4-a716-446655440001',
  consent: { analytics: true, advertising: true },
};

const readyEnvironment = {
  GA4_ENABLED: 'true', GA4_MEASUREMENT_ID: 'G-TEST123', GA4_API_SECRET: 'ga-secret',
  SERVER_GTM_ENABLED: 'true', SERVER_GTM_ENDPOINT: 'https://metrics.example.test/events', SERVER_GTM_ALLOWED_HOSTS: 'metrics.example.test', SERVER_GTM_AUTH_TOKEN: 'gtm-secret',
  META_ENABLED: 'true', META_PIXEL_ID: '1234567890', META_ACCESS_TOKEN: 'meta-secret',
};

describe('server marketing destinations', () => {
  it('dispatches independently to ready consent-matched destinations', async () => {
    const fetcher = jest.fn<ReturnType<typeof fetch>, Parameters<typeof fetch>>(async () => new Response(null, { status: 204 }));
    await expect(dispatchAcquisitionEvent(event, fetcher, readyEnvironment)).resolves.toEqual([
      { destination: 'ga4', result: 'DELIVERED' },
      { destination: 'serverGtm', result: 'DELIVERED' },
      { destination: 'meta', result: 'DELIVERED' },
    ]);
    expect(fetcher).toHaveBeenCalledTimes(3);
  });

  it('disables incomplete, unapproved, and non-consented destinations', async () => {
    const fetcher = jest.fn<ReturnType<typeof fetch>, Parameters<typeof fetch>>(async () => new Response(null, { status: 204 }));
    const environment = { ...readyEnvironment, SERVER_GTM_ALLOWED_HOSTS: 'other.example.test' };
    await dispatchAcquisitionEvent({ ...event, consent: { analytics: true, advertising: false } }, fetcher, environment);
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(String(fetcher.mock.calls[0][0])).toContain('google-analytics.com');
  });

  it('does not route consent updates and contains destination failures', async () => {
    const fetcher = jest.fn<ReturnType<typeof fetch>, Parameters<typeof fetch>>(async () => { throw new Error('destination unavailable'); });
    await expect(dispatchAcquisitionEvent({ ...event, event_name: 'consent_updated' }, fetcher, readyEnvironment)).resolves.toEqual([]);
    await expect(dispatchAcquisitionEvent(event, fetcher, readyEnvironment)).resolves.toEqual([
      { destination: 'ga4', result: 'FAILED' },
      { destination: 'serverGtm', result: 'FAILED' },
      { destination: 'meta', result: 'FAILED' },
    ]);
  });
});