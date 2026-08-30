// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Destination And Environment Matrix
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

export type AcquisitionEvent = Record<string, unknown> & {
  event_id: string;
  event_name: string;
  timestamp: string;
  deduplication_id: string;
  consent: { analytics: boolean; advertising: boolean };
};

type Destination = 'ga4' | 'serverGtm' | 'meta';
export type DestinationResult = { destination: Destination; result: 'DISABLED' | 'DELIVERED' | 'FAILED' };
type MarketingEnvironment = Readonly<Record<string, string | undefined>>;

function enabled(value: string | undefined): boolean {
  return value === 'true';
}

function approvedGtmEndpoint(environment: MarketingEnvironment): string | undefined {
  if (!enabled(environment.SERVER_GTM_ENABLED) || !environment.SERVER_GTM_AUTH_TOKEN) return undefined;
  try {
    const endpoint = new URL(environment.SERVER_GTM_ENDPOINT ?? '');
    const hosts = new Set((environment.SERVER_GTM_ALLOWED_HOSTS ?? '').split(',').map((host) => host.trim()).filter(Boolean));
    return endpoint.protocol === 'https:' && hosts.has(endpoint.hostname) ? endpoint.toString() : undefined;
  } catch {
    return undefined;
  }
}

async function deliver(destination: Destination, request: () => Promise<Response>): Promise<DestinationResult> {
  try {
    const response = await request();
    return { destination, result: response.ok ? 'DELIVERED' : 'FAILED' };
  } catch {
    return { destination, result: 'FAILED' };
  }
}

export async function dispatchAcquisitionEvent(
  event: AcquisitionEvent,
  fetcher: typeof fetch = fetch,
  environment: MarketingEnvironment = process.env,
): Promise<DestinationResult[]> {
  if (event.event_name === 'consent_updated') return [];
  const deliveries: Promise<DestinationResult>[] = [];

  if (event.consent.analytics && enabled(environment.GA4_ENABLED) && /^G-[A-Z0-9]+$/.test(environment.GA4_MEASUREMENT_ID ?? '') && environment.GA4_API_SECRET) {
    const endpoint = new URL('https://www.google-analytics.com/mp/collect');
    endpoint.searchParams.set('measurement_id', environment.GA4_MEASUREMENT_ID as string);
    endpoint.searchParams.set('api_secret', environment.GA4_API_SECRET);
    deliveries.push(deliver('ga4', () => fetcher(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: event.deduplication_id, events: [{ name: event.event_name, params: event }] }),
      signal: AbortSignal.timeout(2_000),
    })));
  }

  const gtmEndpoint = approvedGtmEndpoint(environment);
  if (event.consent.analytics && gtmEndpoint) {
    deliveries.push(deliver('serverGtm', () => fetcher(gtmEndpoint, {
      method: 'POST',
      headers: { Authorization: `Bearer ${environment.SERVER_GTM_AUTH_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
      signal: AbortSignal.timeout(2_000),
    })));
  }

  if (event.consent.advertising && enabled(environment.META_ENABLED) && /^\d{5,30}$/.test(environment.META_PIXEL_ID ?? '') && environment.META_ACCESS_TOKEN) {
    const endpoint = new URL(`https://graph.facebook.com/v21.0/${environment.META_PIXEL_ID}/events`);
    endpoint.searchParams.set('access_token', environment.META_ACCESS_TOKEN);
    deliveries.push(deliver('meta', () => fetcher(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: [{ event_name: event.event_name, event_time: Math.floor(Date.parse(event.timestamp) / 1000), event_id: event.event_id, action_source: 'website', custom_data: event }] }),
      signal: AbortSignal.timeout(2_000),
    })));
  }

  return Promise.all(deliveries);
}