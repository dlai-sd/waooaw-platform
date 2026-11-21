import 'server-only';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { NextResponse, type NextRequest } from 'next/server';
import {
  Configuration,
  PricingDraftsApi,
  PricingReportsApi,
  PricingSafetyApi,
  PricingVersionsApi,
} from '@/lib/api/generated/pricing-admin-v1/src';
import {
  pricingAccess,
  pricingQueryNames,
  pricingRouteFor,
  pricingRouteWrites,
  type PricingAccess,
} from '@/lib/pricing-admin';
import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { readRequestJson } from '@/lib/server-failure-boundary';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const noStore = { 'Cache-Control': 'no-store' } as const;
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const maximumBodyLength = 262_144;
const writeLimitPerMinute = 30;
const writeWindows = new Map<string, number[]>();

export function withinPricingWriteLimit(subject: string, now = Date.now()): boolean {
  const recent = (writeWindows.get(subject) ?? []).filter((timestamp) => now - timestamp < 60_000);
  if (recent.length >= writeLimitPerMinute) return false;
  recent.push(now);
  writeWindows.set(subject, recent);
  return true;
}

export function resetPricingWriteLimit(): void {
  writeWindows.clear();
}

export function pricingApis(accessToken: string) {
  const configuration = new Configuration({ basePath: businessPlatformUrl, accessToken });
  return {
    drafts: new PricingDraftsApi(configuration),
    versions: new PricingVersionsApi(configuration),
    safety: new PricingSafetyApi(configuration),
    reports: new PricingReportsApi(configuration),
  };
}

function problem(status: number, code: string, title: string, correlationId: string) {
  return NextResponse.json(
    { type: 'about:blank', title, status, code, correlationId },
    { status, headers: { ...noStore, 'X-Correlation-ID': correlationId } }
  );
}

function subjectOf(accessToken: string): string {
  try {
    const claims = JSON.parse(Buffer.from(accessToken.split('.')[1] ?? '', 'base64url').toString('utf8'));
    return typeof claims.sub === 'string' && claims.sub.length > 0 ? claims.sub : 'unknown';
  } catch {
    return 'unknown';
  }
}

export async function proxyPricingAdmin(
  request: NextRequest,
  accessToken: string,
  segments: readonly string[]
): Promise<Response> {
  const method = request.method.toUpperCase();
  const correlationHeader = request.headers.get('x-correlation-id');
  const correlationId =
    correlationHeader && uuidPattern.test(correlationHeader) ? correlationHeader : crypto.randomUUID();
  const access: PricingAccess = pricingAccess(accessToken);
  if (!access.administrator) {
    return problem(403, 'PRICING_FORBIDDEN', 'Pricing administration is not permitted.', correlationId);
  }
  const route = pricingRouteFor(method, segments);
  if (!route) return problem(404, 'PRICING_NOT_FOUND', 'The pricing route was not found.', correlationId);
  if (route.founderOnly && !access.founder) {
    return problem(403, 'PRICING_FORBIDDEN', 'Only the Founder may do this.', correlationId);
  }

  const headers: Record<string, string> = {
    Accept: 'application/json',
    Authorization: `Bearer ${accessToken}`,
    'X-Correlation-ID': correlationId,
  };
  let body: string | undefined;
  if (pricingRouteWrites(route)) {
    const idempotencyKey = request.headers.get('idempotency-key');
    if (!idempotencyKey || !uuidPattern.test(idempotencyKey)) {
      return problem(400, 'PRICING_REQUEST_INVALID', 'An idempotency key is required.', correlationId);
    }
    if (!withinPricingWriteLimit(subjectOf(accessToken))) {
      return problem(429, 'PRICING_RATE_LIMITED', 'Too many pricing changes. Wait before trying again.', correlationId);
    }
    const parsed = await readRequestJson(request).catch(() => undefined);
    body = parsed === undefined ? undefined : JSON.stringify(parsed);
    if (body === undefined || body.length > maximumBodyLength) {
      return problem(400, 'PRICING_REQUEST_INVALID', 'The request body is missing or too large.', correlationId);
    }
    headers['Idempotency-Key'] = idempotencyKey;
    headers['Content-Type'] = 'application/json';
  }

  const query = new URLSearchParams();
  for (const name of pricingQueryNames) {
    const value = request.nextUrl.searchParams.get(name);
    if (value !== null && /^[A-Za-z0-9._:~=|+-]{1,300}$/.test(value)) query.set(name, value);
  }
  const target = `${businessPlatformUrl}/api/v1/admin/pricing/${segments.join('/')}${query.toString().length > 0 ? `?${query.toString()}` : ''}`;

  let upstream: Response;
  try {
    upstream = await fetch(target, { method, headers, body, cache: 'no-store' });
  } catch (error) {
    logServerFailure('web.admin.pricing.request_failed', error);
    return problem(503, 'PRICING_UNAVAILABLE', 'Pricing administration is temporarily unavailable.', correlationId);
  }
  const payload = await readServerResponse(upstream, 'web.admin.pricing.response_invalid', {
    type: 'about:blank',
    title: 'Pricing administration is temporarily unavailable.',
    status: upstream.status,
    code: 'PRICING_UNAVAILABLE',
    correlationId,
  });
  const responseHeaders: Record<string, string> = { ...noStore, 'X-Correlation-ID': correlationId };
  const etag = upstream.headers.get('etag');
  if (etag) responseHeaders.ETag = etag;
  return NextResponse.json(payload ?? {}, { status: upstream.status, headers: responseHeaders });
}
