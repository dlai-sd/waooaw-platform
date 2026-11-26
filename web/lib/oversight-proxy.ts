import 'server-only';

// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R007, WC171-R008, WC171-R009
// Constitutional basis: C-001, C-023, C-059, C-063

import { NextResponse, type NextRequest } from 'next/server';
import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { readRequestJson } from '@/lib/server-failure-boundary';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const noStore = { 'Cache-Control': 'no-store' } as const;
const maximumBodyLength = 4_096;
const id = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';
const code = '[A-Z][A-Z0-9_]{2,159}';

type Method = 'GET' | 'POST' | 'PUT';
type Route = { method: Method; pattern: RegExp };

// Only these exact routes are forwarded. Nothing else under the prefix reaches the Business Platform.
export const alertControlRoutes: readonly Route[] = [
  { method: 'GET', pattern: /^alerts$/ },
  { method: 'POST', pattern: new RegExp(`^alerts/${id}/snooze$`) },
  { method: 'GET', pattern: /^categories$/ },
  { method: 'PUT', pattern: new RegExp(`^categories/${code}$`) },
];

export const operationsRoutes: readonly Route[] = [
  { method: 'GET', pattern: /^overview$/ },
  { method: 'GET', pattern: /^blocked-messages$/ },
  { method: 'GET', pattern: /^blocked-messages\/history$/ },
  { method: 'POST', pattern: new RegExp(`^blocked-messages/${id}/resolve$`) },
  { method: 'GET', pattern: /^pages$/ },
  { method: 'GET', pattern: /^customers$/ },
  { method: 'POST', pattern: new RegExp(`^pages/${code}/acknowledge$`) },
  { method: 'GET', pattern: new RegExp(`^relationships/${id}/work-timeline$`) },
  { method: 'GET', pattern: new RegExp(`^relationships/${id}/spend-chain$`) },
  { method: 'POST', pattern: new RegExp(`^relationships/${id}/spend-discrepancies/${id}/resolve$`) },
];

export function oversightRouteAllowed(routes: readonly Route[], method: string, segments: readonly string[]): boolean {
  const path = segments.join('/');
  return routes.some((route) => route.method === method && route.pattern.test(path));
}

const defaultQueryValue = /^[A-Za-z0-9-]{1,64}$/;
// Only these query values are forwarded, each with the narrowest shape it may have.
const forwardedQuery: Record<string, RegExp> = {
  relationshipId: defaultQueryValue,
  includeSnoozed: defaultQueryValue,
  limit: defaultQueryValue,
  tenantId: defaultQueryValue,
  name: /^[\p{L}\p{N} .'-]{1,120}$/u,
  contact: /^[A-Za-z0-9@.+_ -]{1,254}$/,
  status: /^[A-Z_]{1,32}$/,
  cursor: /^[A-Za-z0-9_-]{1,200}$/,
  pageSize: /^[0-9]{1,2}$/,
};

export async function proxyOversight(
  request: NextRequest,
  accessToken: string,
  upstreamPrefix: string,
  routes: readonly Route[],
  segments: readonly string[]
): Promise<Response> {
  const method = request.method.toUpperCase();
  if (!oversightRouteAllowed(routes, method, segments))
    return NextResponse.json(
      { code: 'NOT_FOUND', title: 'The route was not found.' },
      { status: 404, headers: noStore }
    );
  const headers: Record<string, string> = { Accept: 'application/json', Authorization: `Bearer ${accessToken}` };
  let body: string | undefined;
  if (method !== 'GET') {
    const parsed = await readRequestJson(request).catch(() => undefined);
    body = parsed === undefined ? undefined : JSON.stringify(parsed);
    if (body === undefined || body.length > maximumBodyLength)
      return NextResponse.json(
        { code: 'REQUEST_INVALID', title: 'The request body is missing or too large.' },
        { status: 400, headers: noStore }
      );
    headers['Content-Type'] = 'application/json';
    const key = request.headers.get('Idempotency-Key');
    if (key && new RegExp(`^${id}$`).test(key)) headers['Idempotency-Key'] = key;
  }
  const query = new URLSearchParams();
  for (const [name, pattern] of Object.entries(forwardedQuery)) {
    const value = request.nextUrl.searchParams.get(name);
    if (value && pattern.test(value)) query.set(name, value);
  }
  const suffix = query.size > 0 ? `?${query.toString()}` : '';
  let upstream: Response;
  try {
    upstream = await fetch(`${businessPlatformUrl}${upstreamPrefix}/${segments.join('/')}${suffix}`, {
      method,
      headers,
      body,
      cache: 'no-store',
    });
  } catch (error) {
    logServerFailure('web.oversight.request_failed', error);
    return NextResponse.json(
      { code: 'UNAVAILABLE', title: 'This is not available right now.' },
      { status: 503, headers: noStore }
    );
  }
  const payload = await readServerResponse(upstream, 'web.oversight.response_invalid', {
    code: 'UNAVAILABLE',
    title: 'This is not available right now.',
  });
  return NextResponse.json(payload, { status: upstream.status, headers: noStore });
}
