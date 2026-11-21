import 'server-only';

// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063

import { NextResponse, type NextRequest } from 'next/server';
import {
  noPlatformAccess,
  platformAccessFrom,
  platformAccessRouteAllowed,
  type PlatformAccess,
} from '@/lib/platform-access';
import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { readRequestJson } from '@/lib/server-failure-boundary';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const noStore = { 'Cache-Control': 'no-store' } as const;
const maximumBodyLength = 8_192;

// The Business Platform owns who holds a staff role. A token that only claims a role gets nothing, and an
// unreachable Business Platform grants nothing.
export async function resolvePlatformAccess(accessToken: string | undefined): Promise<PlatformAccess> {
  if (!accessToken) return noPlatformAccess;
  try {
    const response = await fetch(`${businessPlatformUrl}/api/v1/platform/me/roles`, {
      headers: { Accept: 'application/json', Authorization: `Bearer ${accessToken}` },
      cache: 'no-store',
    });
    if (!response.ok) return noPlatformAccess;
    return platformAccessFrom(await response.json());
  } catch (error) {
    logServerFailure('web.platform_access.roles_failed', error);
    return noPlatformAccess;
  }
}

export async function proxyPlatformAccess(
  request: NextRequest,
  accessToken: string,
  segments: readonly string[]
): Promise<Response> {
  const method = request.method.toUpperCase();
  if (!platformAccessRouteAllowed(method, segments)) {
    return NextResponse.json(
      { code: 'PLATFORM_ACCESS_NOT_FOUND', title: 'The route was not found.' },
      { status: 404, headers: noStore }
    );
  }
  const headers: Record<string, string> = { Accept: 'application/json', Authorization: `Bearer ${accessToken}` };
  let body: string | undefined;
  if (method === 'POST') {
    const parsed = await readRequestJson(request).catch(() => undefined);
    body = parsed === undefined ? undefined : JSON.stringify(parsed);
    if (body === undefined || body.length > maximumBodyLength) {
      return NextResponse.json(
        { code: 'PLATFORM_ACCESS_REQUEST_INVALID', title: 'The request body is missing or too large.' },
        { status: 400, headers: noStore }
      );
    }
    headers['Content-Type'] = 'application/json';
  }
  const status = request.nextUrl.searchParams.get('status');
  const query = status && /^[A-Z]{1,10}$/.test(status) ? `?status=${status}` : '';
  let upstream: Response;
  try {
    upstream = await fetch(`${businessPlatformUrl}/api/v1/platform/${segments.join('/')}${query}`, {
      method,
      headers,
      body,
      cache: 'no-store',
    });
  } catch (error) {
    logServerFailure('web.platform_access.request_failed', error);
    return NextResponse.json(
      { code: 'PLATFORM_ACCESS_UNAVAILABLE', title: 'Access management is temporarily unavailable.' },
      { status: 503, headers: noStore }
    );
  }
  const payload = await readServerResponse(upstream, 'web.platform_access.response_invalid', {
    code: 'PLATFORM_ACCESS_UNAVAILABLE',
    title: 'Access management is temporarily unavailable.',
  });
  return NextResponse.json(payload ?? {}, { status: upstream.status, headers: noStore });
}
