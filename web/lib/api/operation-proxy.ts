import 'server-only';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R028, R030, R032
// Constitutional basis: C-001, C-023, C-059, C-063

import { NextResponse, type NextRequest } from 'next/server';
import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { readRequestJson } from '@/lib/server-failure-boundary';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const noStore = { 'Cache-Control': 'no-store' } as const;
const uuid = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';
const uuidPattern = new RegExp(`^${uuid}$`);
const segment = '[A-Za-z0-9_:-]{1,128}';
const maximumBodyLength = 65_536;

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH';
type Route = { method: Method; pattern: RegExp };

// The customer routes of Agent Operation; nothing else is proxied.
const customerRoutes: readonly Route[] = [
  { method: 'GET', pattern: /^(frame|calendar|plan-tree|items|context)$/ },
  { method: 'GET', pattern: new RegExp(`^items/${uuid}/versions$`) },
  { method: 'PUT', pattern: /^(mode|publish-authority)$/ },
  { method: 'PUT', pattern: new RegExp(`^layers/${segment}$`) },
  { method: 'PUT', pattern: new RegExp(`^platforms/${segment}/answer$`) },
  { method: 'PUT', pattern: new RegExp(`^goals/${segment}$`) },
  { method: 'PATCH', pattern: new RegExp(`^items/${uuid}$`) },
  { method: 'POST', pattern: /^(tour-seen|layers|items|schedule|conversation\/chats)$/ },
  {
    method: 'POST',
    pattern: new RegExp(`^items/${uuid}/(accept|hide|restore|hand-over|take-back|undo|approve|reject|move)$`),
  },
  { method: 'POST', pattern: new RegExp(`^labels/${uuid}/confirm$`) },
  { method: 'POST', pattern: new RegExp(`^platforms/${segment}/test$`) },
  { method: 'POST', pattern: new RegExp(`^goals/${segment}/decision$`) },
  { method: 'POST', pattern: new RegExp(`^digests/${uuid}/decision$`) },
  { method: 'POST', pattern: new RegExp(`^slots/${uuid}/publish$`) },
];

const adminRoutes: readonly Route[] = [
  { method: 'GET', pattern: /^(settings|share|attention)$/ },
  { method: 'PUT', pattern: /^settings$/ },
];

const queryNames = ['from', 'to', 'includeHidden', 'mode', 'view', 'selected', 'kind'] as const;

export function operationRouteAllowed(method: string, segments: readonly string[], admin = false): boolean {
  const path = segments.join('/');
  return (admin ? adminRoutes : customerRoutes).some((route) => route.method === method && route.pattern.test(path));
}

function problem(status: number, code: string, title: string, correlationId: string) {
  return NextResponse.json(
    { type: 'about:blank', title, status, code, correlationId },
    { status, headers: { ...noStore, 'X-Correlation-ID': correlationId } }
  );
}

// Only a known code and plain detail cross back to the browser; the platform's wording is already customer-safe.
function relay(payload: unknown, status: number, correlationId: string) {
  const source = payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {};
  if (status < 400)
    return NextResponse.json(payload ?? {}, { status, headers: { ...noStore, 'X-Correlation-ID': correlationId } });
  const code =
    typeof source.code === 'string' && /^[A-Z_]{3,64}$/.test(source.code) ? source.code : 'OPERATION_UNAVAILABLE';
  const detail = typeof source.detail === 'string' && source.detail.length <= 400 ? source.detail : undefined;
  const nextMode =
    typeof source.nextMode === 'string' && /^[A-Z_]{3,20}$/.test(source.nextMode) ? source.nextMode : undefined;
  return NextResponse.json(
    { type: 'about:blank', status, code, detail, nextMode, correlationId },
    { status, headers: { ...noStore, 'X-Correlation-ID': correlationId } }
  );
}

async function forward(
  request: NextRequest,
  accessToken: string,
  target: string,
  segments: readonly string[],
  admin: boolean
): Promise<Response> {
  const method = request.method.toUpperCase() as Method;
  const correlationHeader = request.headers.get('x-correlation-id');
  const correlationId =
    correlationHeader && uuidPattern.test(correlationHeader) ? correlationHeader : crypto.randomUUID();
  if (!operationRouteAllowed(method, segments, admin)) {
    return problem(404, 'OPERATION_REQUEST_INVALID', 'That route was not found.', correlationId);
  }
  const headers: Record<string, string> = {
    Accept: 'application/json',
    Authorization: `Bearer ${accessToken}`,
    'X-Correlation-ID': correlationId,
  };
  let body: string | undefined;
  if (method !== 'GET') {
    const key = request.headers.get('idempotency-key');
    if (key && uuidPattern.test(key)) headers['Idempotency-Key'] = key;
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(await readRequestJson(request));
    if (body.length > maximumBodyLength)
      return problem(400, 'OPERATION_REQUEST_INVALID', 'The request is too large.', correlationId);
  }
  const query = new URLSearchParams();
  for (const name of queryNames) {
    const value = request.nextUrl.searchParams.get(name);
    if (value !== null && /^[A-Za-z0-9_.:-]{1,64}$/.test(value)) query.set(name, value);
  }
  const url = `${target}/${segments.join('/')}${query.size > 0 ? `?${query.toString()}` : ''}`;
  let upstream: Response;
  try {
    upstream = await fetch(url, { method, headers, body, cache: 'no-store' });
  } catch (error) {
    logServerFailure('web.agent_operation.request_failed', error);
    return problem(503, 'OPERATION_UNAVAILABLE', 'Agent operation is temporarily unavailable.', correlationId);
  }
  const payload = await readServerResponse(upstream, 'web.agent_operation.response_invalid', {
    code: 'OPERATION_UNAVAILABLE',
    status: upstream.status,
  });
  return relay(payload, upstream.status, correlationId);
}

export function proxyOperation(
  request: NextRequest,
  accessToken: string,
  relationshipId: string,
  segments: readonly string[]
) {
  if (!uuidPattern.test(relationshipId)) {
    return Promise.resolve(problem(404, 'OPERATION_REQUEST_INVALID', 'That route was not found.', crypto.randomUUID()));
  }
  return forward(
    request,
    accessToken,
    `${businessPlatformUrl}/api/v1/employment/relationships/${relationshipId}/operation`,
    segments,
    false
  );
}

export function proxyOperationAdmin(request: NextRequest, accessToken: string, segments: readonly string[]) {
  return forward(request, accessToken, `${businessPlatformUrl}/api/v1/admin/agent-operation`, segments, true);
}
