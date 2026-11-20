import 'server-only';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-04
// Constitutional basis: C-001, C-023, C-059, C-063, ADR-051

import { NextResponse, type NextRequest } from 'next/server';
import { workbenchExperienceCapabilities } from '@/lib/api/workbench-capabilities';
import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { readRequestJson } from '@/lib/server-failure-boundary';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const noStore = { 'Cache-Control': 'no-store' } as const;
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const segment = '[A-Za-z0-9_:-][A-Za-z0-9._:-]{0,127}';

export { workbenchExperienceCapabilities };

type Method = 'GET' | 'POST';

const allowedRoutes: ReadonlyArray<{ method: Method; pattern: RegExp }> = [
  { method: 'GET', pattern: /^$/ },
  { method: 'GET', pattern: /^goals$/ },
  { method: 'GET', pattern: new RegExp(`^goals/${segment}$`) },
  { method: 'GET', pattern: new RegExp(`^goals/${segment}/versions$`) },
  { method: 'GET', pattern: /^plans\/current$/ },
  { method: 'GET', pattern: /^capabilities$/ },
  { method: 'GET', pattern: /^work-items$/ },
  { method: 'GET', pattern: /^decisions$/ },
  { method: 'GET', pattern: /^monitor$/ },
  { method: 'GET', pattern: /^monitor\/narratives$/ },
  { method: 'GET', pattern: /^wallet$/ },
  { method: 'GET', pattern: /^evidence$/ },
  { method: 'POST', pattern: /^goals$/ },
  { method: 'POST', pattern: new RegExp(`^goals/${segment}/revisions$`) },
  { method: 'POST', pattern: /^plans$/ },
  { method: 'POST', pattern: new RegExp(`^plans/${segment}/accept$`) },
  { method: 'POST', pattern: new RegExp(`^capabilities/${segment}/commands$`) },
  { method: 'POST', pattern: new RegExp(`^decisions/${segment}/resolve$`) },
  { method: 'POST', pattern: /^topups$/ },
  { method: 'POST', pattern: /^evidence\/exports$/ },
  { method: 'POST', pattern: /^controls\/stop$/ },
  { method: 'POST', pattern: /^controls\/pause$/ },
  { method: 'POST', pattern: /^handoffs$/ },
  { method: 'POST', pattern: /^handoffs\/consume$/ },
];

export function workbenchRouteAllowed(method: string, segments: readonly string[]): boolean {
  const path = segments.join('/');
  return allowedRoutes.some((route) => route.method === method && route.pattern.test(path));
}

function problem(status: number, code: string, title: string, correlationId: string) {
  return NextResponse.json(
    { type: 'about:blank', title, status, code, correlationId },
    { status, headers: { ...noStore, 'X-Correlation-ID': correlationId } }
  );
}

function validUuid(value: string | null): value is string {
  return value !== null && uuidPattern.test(value);
}

export async function proxyWorkbench(
  request: NextRequest,
  accessToken: string,
  relationshipId: string,
  segments: readonly string[]
): Promise<Response> {
  const method = request.method.toUpperCase();
  const correlationHeader = request.headers.get('x-correlation-id');
  const correlationId = validUuid(correlationHeader) ? correlationHeader : crypto.randomUUID();
  if (!uuidPattern.test(relationshipId) || !workbenchRouteAllowed(method, segments)) {
    return problem(404, 'WORKBENCH_REQUEST_INVALID', 'Workbench route was not found.', correlationId);
  }

  const headers: Record<string, string> = {
    Accept: 'application/json',
    Authorization: `Bearer ${accessToken}`,
    'X-Correlation-ID': correlationId,
    'X-Experience-Capabilities': workbenchExperienceCapabilities,
  };
  let body: string | undefined;
  if (method === 'POST') {
    const idempotencyKey = request.headers.get('idempotency-key');
    if (!validUuid(idempotencyKey)) {
      return problem(400, 'WORKBENCH_REQUEST_INVALID', 'An idempotency key is required.', correlationId);
    }
    headers['Idempotency-Key'] = idempotencyKey;
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(await readRequestJson(request));
    if (body.length > 65536) {
      return problem(400, 'WORKBENCH_REQUEST_INVALID', 'The request is too large.', correlationId);
    }
  }

  const query = new URLSearchParams();
  for (const name of ['cursor', 'limit']) {
    const value = request.nextUrl.searchParams.get(name);
    if (value !== null && /^[A-Za-z0-9._~=-]{1,512}$/.test(value)) query.set(name, value);
  }
  const suffix = segments.length > 0 ? `/${segments.join('/')}` : '';
  const target = `${businessPlatformUrl}/api/v1/employment/relationships/${relationshipId}/workbench${suffix}${query.toString().length > 0 ? `?${query.toString()}` : ''}`;

  let upstream: Response;
  try {
    upstream = await fetch(target, { method, headers, body, cache: 'no-store' });
  } catch (error) {
    logServerFailure('web.relationships.relationshipid.workbench.request_failed', error);
    return problem(503, 'WORKBENCH_UNAVAILABLE', 'The workbench is temporarily unavailable.', correlationId);
  }

  const payload = await readServerResponse(upstream, 'web.relationships.relationshipid.workbench.response_invalid', {
    type: 'about:blank',
    title: 'The workbench is temporarily unavailable.',
    status: upstream.status,
    code: 'WORKBENCH_UNAVAILABLE',
    correlationId,
  });
  const responseHeaders: Record<string, string> = { ...noStore, 'X-Correlation-ID': correlationId };
  const etag = upstream.headers.get('etag');
  if (etag) responseHeaders.ETag = etag;
  return NextResponse.json(payload ?? {}, { status: upstream.status, headers: responseHeaders });
}
