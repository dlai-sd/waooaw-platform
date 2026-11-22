import 'server-only';

// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R002, WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { NextResponse, type NextRequest } from 'next/server';
import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { readRequestJson } from '@/lib/server-failure-boundary';
import type { ProviderSummary } from '@/lib/provider-admin-client';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const noStore = { 'Cache-Control': 'no-store' } as const;
const uuid = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';
const uuidPattern = new RegExp(`^${uuid}$`);
const maximumBodyLength = 20_480;
const writeLimitPerMinute = 30;
const writeWindows = new Map<string, number[]>();

type ProviderRoute = {
  operationId: string;
  method: 'GET' | 'POST';
  pattern: RegExp;
};

// The six operations of the Founder provider registry; nothing else is ever proxied.
const providerRoutes: readonly ProviderRoute[] = [
  { operationId: 'listProviders', method: 'GET', pattern: /^$/ },
  { operationId: 'createProvider', method: 'POST', pattern: /^$/ },
  {
    operationId: 'listCredentialVersions',
    method: 'GET',
    pattern: new RegExp(`^${uuid}/credentials$`),
  },
  {
    operationId: 'testCredential',
    method: 'POST',
    pattern: new RegExp(`^${uuid}/credentials/test$`),
  },
  {
    operationId: 'saveCredential',
    method: 'POST',
    pattern: new RegExp(`^${uuid}/credentials$`),
  },
  {
    operationId: 'activateCredentialVersion',
    method: 'POST',
    pattern: new RegExp(`^${uuid}/credentials/${uuid}/activate$`),
  },
];

export function providerRouteFor(method: string, segments: readonly string[]): ProviderRoute | undefined {
  const path = segments.join('/');
  return providerRoutes.find((route) => route.method === method.toUpperCase() && route.pattern.test(path));
}

export function withinProviderWriteLimit(subject: string, now = Date.now()): boolean {
  const recent = (writeWindows.get(subject) ?? []).filter((timestamp) => now - timestamp < 60_000);
  if (recent.length >= writeLimitPerMinute) return false;
  recent.push(now);
  writeWindows.set(subject, recent);
  return true;
}

export function resetProviderWriteLimit(): void {
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

const fallbackProblems: Record<number, { code: string; title: string }> = {
  400: { code: 'PROVIDER_INVALID', title: 'The request was not valid.' },
  401: { code: 'PROVIDER_FORBIDDEN', title: 'Secure sign in is required.' },
  403: {
    code: 'PROVIDER_FORBIDDEN',
    title: 'Provider administration is not permitted.',
  },
  404: { code: 'PROVIDER_NOT_FOUND', title: 'The provider was not found.' },
  409: {
    code: 'PROVIDER_CONFLICT',
    title: 'The provider already exists or changed.',
  },
};

// Only the problem code and title cross back to the browser; upstream detail text is never relayed.
function relayedProblem(upstream: unknown, status: number, correlationId: string) {
  const source = upstream && typeof upstream === 'object' ? (upstream as Record<string, unknown>) : {};
  const fallback = fallbackProblems[status] ?? {
    code: 'PROVIDER_VAULT_UNAVAILABLE',
    title: 'Provider administration is temporarily unavailable.',
  };
  const code = typeof source.code === 'string' && /^[A-Z_]{3,64}$/.test(source.code) ? source.code : fallback.code;
  const title =
    typeof source.title === 'string' && source.title.length > 0 && source.title.length <= 200
      ? source.title
      : fallback.title;
  return problem(status, code, title, correlationId);
}

export async function proxyProviderAdmin(
  request: NextRequest,
  accessToken: string,
  segments: readonly string[]
): Promise<Response> {
  const method = request.method.toUpperCase();
  const correlationHeader = request.headers.get('x-correlation-id');
  const correlationId =
    correlationHeader && uuidPattern.test(correlationHeader) ? correlationHeader : crypto.randomUUID();
  const route = providerRouteFor(method, segments);
  if (!route) return problem(404, 'PROVIDER_NOT_FOUND', 'The provider route was not found.', correlationId);

  const headers: Record<string, string> = {
    Accept: 'application/json',
    Authorization: `Bearer ${accessToken}`,
    'X-Correlation-ID': correlationId,
  };
  let body: string | undefined;
  if (method === 'POST') {
    if (!withinProviderWriteLimit(subjectOf(accessToken))) {
      return problem(429, 'PROVIDER_RATE_LIMITED', 'Too many changes. Wait before trying again.', correlationId);
    }
    const declared = Number(request.headers.get('content-length') ?? 0);
    if (declared > maximumBodyLength) {
      return problem(413, 'PROVIDER_INVALID', 'The request body is too large.', correlationId);
    }
    const parsed = await readRequestJson(request).catch(() => undefined);
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return problem(400, 'PROVIDER_INVALID', 'The request body is missing or not valid.', correlationId);
    }
    body = JSON.stringify(parsed);
    if (body.length > maximumBodyLength) {
      return problem(413, 'PROVIDER_INVALID', 'The request body is too large.', correlationId);
    }
    headers['Content-Type'] = 'application/json';
  }

  const target = `${businessPlatformUrl}/api/v1/admin/providers${segments.length > 0 ? `/${segments.join('/')}` : ''}`;
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method,
      headers,
      body,
      cache: 'no-store',
    });
  } catch (error) {
    logServerFailure('web.admin.providers.request_failed', error);
    return problem(
      503,
      'PROVIDER_VAULT_UNAVAILABLE',
      'Provider administration is temporarily unavailable.',
      correlationId
    );
  }
  const payload = await readServerResponse(upstream, 'web.admin.providers.response_invalid', {
    title: 'Provider administration is temporarily unavailable.',
    code: 'PROVIDER_VAULT_UNAVAILABLE',
  });
  if (!upstream.ok) return relayedProblem(payload, upstream.status, correlationId);
  return NextResponse.json(payload ?? {}, {
    status: upstream.status,
    headers: { ...noStore, 'X-Correlation-ID': correlationId },
  });
}

export type ProviderListLoad =
  | { kind: 'ready'; providers: ProviderSummary[] }
  | { kind: 'forbidden' }
  | { kind: 'unavailable' };

// Server-component read for the first paint; the browser then uses the same-origin proxy.
export async function loadProviders(accessToken: string): Promise<ProviderListLoad> {
  try {
    const response = await fetch(`${businessPlatformUrl}/api/v1/admin/providers`, {
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      cache: 'no-store',
    });
    if (response.status === 401 || response.status === 403) return { kind: 'forbidden' };
    if (!response.ok) {
      logServerFailure('web.admin.providers.list_failed', new Error('Provider list failed'), {
        status: response.status,
      });
      return { kind: 'unavailable' };
    }
    const providers: unknown = await response.json();
    return Array.isArray(providers)
      ? { kind: 'ready', providers: providers as ProviderSummary[] }
      : { kind: 'unavailable' };
  } catch (error) {
    logServerFailure('web.admin.providers.list_failed', error);
    return { kind: 'unavailable' };
  }
}
