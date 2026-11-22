import 'server-only';

// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R007, WC149-R008, WC149-R009, WC149-R010
// Constitutional basis: C-026, C-059, C-063, C-083

import { NextResponse, type NextRequest } from 'next/server';
import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { readRequestJson } from '@/lib/server-failure-boundary';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const noStore = { 'Cache-Control': 'no-store' } as const;
const uuid = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';
const uuidPattern = new RegExp(`^${uuid}$`);
const maximumBodyLength = 20_480;
const writeLimitPerMinute = 30;
const writeWindows = new Map<string, number[]>();

type ConnectionRoute = { operationId: string; method: 'GET' | 'POST'; pattern: RegExp };

// The four operations a customer can perform; the Meta callback has its own route. Nothing else is proxied.
const connectionRoutes: readonly ConnectionRoute[] = [
  { operationId: 'listConnections', method: 'GET', pattern: /^$/ },
  { operationId: 'startMetaConnection', method: 'POST', pattern: /^meta\/start$/ },
  { operationId: 'revokeConnection', method: 'POST', pattern: new RegExp(`^${uuid}/revoke$`) },
  { operationId: 'publishPost', method: 'POST', pattern: new RegExp(`^${uuid}/publish$`) },
];

export function connectionRouteFor(method: string, segments: readonly string[]): ConnectionRoute | undefined {
  const path = segments.join('/');
  return connectionRoutes.find((route) => route.method === method.toUpperCase() && route.pattern.test(path));
}

export function withinConnectionWriteLimit(subject: string, now = Date.now()): boolean {
  const recent = (writeWindows.get(subject) ?? []).filter((timestamp) => now - timestamp < 60_000);
  if (recent.length >= writeLimitPerMinute) return false;
  recent.push(now);
  writeWindows.set(subject, recent);
  return true;
}

export function resetConnectionWriteLimit(): void {
  writeWindows.clear();
}

function subjectOf(accessToken: string): string {
  try {
    const claims = JSON.parse(Buffer.from(accessToken.split('.')[1] ?? '', 'base64url').toString('utf8'));
    return typeof claims.sub === 'string' && claims.sub.length > 0 ? claims.sub : 'unknown';
  } catch {
    return 'unknown';
  }
}

function problem(status: number, code: string, title: string, correlationId: string) {
  return NextResponse.json(
    { type: 'about:blank', title, status, code, correlationId },
    { status, headers: { ...noStore, 'X-Correlation-ID': correlationId } }
  );
}

const knownProblems: Record<string, string> = {
  CONNECTION_NEEDS_REPAIR: 'The connection needs to be reconnected.',
  CONNECTION_NOT_FOUND: 'The connection was not found.',
  CONNECTION_REVOKED: 'The connection was revoked.',
  CONNECTION_FORBIDDEN: 'Connections are not permitted for this account.',
  CONNECTION_INVALID: 'The request was not valid.',
  CONNECTION_RATE_LIMITED: 'Too many requests. Wait before trying again.',
  CONNECTION_UNAVAILABLE: 'Connections are temporarily unavailable.',
};

const fallbackProblems: Record<number, string> = {
  400: 'CONNECTION_INVALID',
  401: 'CONNECTION_FORBIDDEN',
  403: 'CONNECTION_FORBIDDEN',
  404: 'CONNECTION_NOT_FOUND',
  409: 'CONNECTION_INVALID',
  429: 'CONNECTION_RATE_LIMITED',
};

// Only a known problem code crosses back to the browser; upstream titles and detail text (which can carry provider messages) are dropped.
function relayedProblem(upstream: unknown, status: number, correlationId: string) {
  const source = upstream && typeof upstream === 'object' ? (upstream as Record<string, unknown>) : {};
  const upstreamCode = typeof source.code === 'string' ? source.code : '';
  const code = Object.hasOwn(knownProblems, upstreamCode)
    ? upstreamCode
    : (fallbackProblems[status] ?? 'CONNECTION_UNAVAILABLE');
  return problem(status, code, knownProblems[code], correlationId);
}

export async function proxyProviderConnections(
  request: NextRequest,
  accessToken: string,
  segments: readonly string[]
): Promise<Response> {
  const method = request.method.toUpperCase();
  const correlationHeader = request.headers.get('x-correlation-id');
  const correlationId =
    correlationHeader && uuidPattern.test(correlationHeader) ? correlationHeader : crypto.randomUUID();
  const route = connectionRouteFor(method, segments);
  if (!route) return problem(404, 'CONNECTION_NOT_FOUND', knownProblems.CONNECTION_NOT_FOUND, correlationId);

  const headers: Record<string, string> = {
    Accept: 'application/json',
    Authorization: `Bearer ${accessToken}`,
    'X-Correlation-ID': correlationId,
  };
  let body: string | undefined;
  if (method === 'POST') {
    if (!withinConnectionWriteLimit(subjectOf(accessToken))) {
      return problem(429, 'CONNECTION_RATE_LIMITED', knownProblems.CONNECTION_RATE_LIMITED, correlationId);
    }
    const declared = Number(request.headers.get('content-length') ?? 0);
    if (declared > maximumBodyLength) {
      return problem(413, 'CONNECTION_INVALID', knownProblems.CONNECTION_INVALID, correlationId);
    }
    const parsed = await readRequestJson(request).catch(() => undefined);
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return problem(400, 'CONNECTION_INVALID', knownProblems.CONNECTION_INVALID, correlationId);
    }
    body = JSON.stringify(parsed);
    if (body.length > maximumBodyLength) {
      return problem(413, 'CONNECTION_INVALID', knownProblems.CONNECTION_INVALID, correlationId);
    }
    headers['Content-Type'] = 'application/json';
  }

  const target = `${businessPlatformUrl}/api/v1/provider-connections${segments.length > 0 ? `/${segments.join('/')}` : ''}`;
  let upstream: Response;
  try {
    upstream = await fetch(target, { method, headers, body, cache: 'no-store' });
  } catch (error) {
    logServerFailure('web.provider_connections.request_failed', error);
    return problem(503, 'CONNECTION_UNAVAILABLE', knownProblems.CONNECTION_UNAVAILABLE, correlationId);
  }
  if (upstream.status === 204) {
    return new Response(null, { status: 204, headers: { ...noStore, 'X-Correlation-ID': correlationId } });
  }
  const payload = await readServerResponse(upstream, 'web.provider_connections.response_invalid', {
    code: 'CONNECTION_UNAVAILABLE',
  });
  if (!upstream.ok) return relayedProblem(payload, upstream.status, correlationId);
  return NextResponse.json(payload ?? {}, {
    status: upstream.status,
    headers: { ...noStore, 'X-Correlation-ID': correlationId },
  });
}

const callbackErrors = [
  'denied',
  'invalid_request',
  'state_invalid',
  'signin_required',
  'unavailable',
  'failed',
] as const;
type CallbackError = (typeof callbackErrors)[number];

const codePattern = /^[^\s]{1,2048}$/;
const statePattern = /^[A-Za-z0-9._~\-]{8,512}$/;

function callbackRedirect(request: NextRequest, query: string): NextResponse {
  const base = process.env.NEXTAUTH_URL ?? request.nextUrl.origin;
  return NextResponse.redirect(new URL(`/connections?${query}`, base), {
    status: 303,
    headers: { ...noStore, 'Referrer-Policy': 'no-referrer' },
  });
}

function failed(request: NextRequest, error: CallbackError): NextResponse {
  return callbackRedirect(request, `error=${error}`);
}

// The Meta redirect URI target. It only ever redirects to /connections with a fixed code; the OAuth code and provider messages are never echoed.
export async function completeMetaCallback(request: NextRequest, accessToken: string | undefined): Promise<Response> {
  const query = request.nextUrl.searchParams;
  if (query.has('error') || query.has('error_reason')) return failed(request, 'denied');
  if (!accessToken) return failed(request, 'signin_required');
  const code = query.get('code') ?? '';
  const state = query.get('state') ?? '';
  if (!codePattern.test(code) || !statePattern.test(state)) return failed(request, 'invalid_request');
  if (!withinConnectionWriteLimit(subjectOf(accessToken))) return failed(request, 'unavailable');

  let upstream: Response;
  try {
    upstream = await fetch(`${businessPlatformUrl}/api/v1/provider-connections/meta/callback`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        'X-Correlation-ID': crypto.randomUUID(),
      },
      body: JSON.stringify({ code, state }),
      cache: 'no-store',
    });
  } catch (error) {
    logServerFailure('web.provider_connections.callback_failed', error);
    return failed(request, 'unavailable');
  }
  if (upstream.ok) return callbackRedirect(request, 'connected=meta');
  if (upstream.status === 401 || upstream.status === 403) return failed(request, 'signin_required');
  if (upstream.status >= 500) {
    logServerFailure('web.provider_connections.callback_failed', new Error('Callback failed'), {
      status: upstream.status,
    });
    return failed(request, 'unavailable');
  }
  if (upstream.status === 400 || upstream.status === 404 || upstream.status === 409 || upstream.status === 410) {
    return failed(request, 'state_invalid');
  }
  return failed(request, 'failed');
}
