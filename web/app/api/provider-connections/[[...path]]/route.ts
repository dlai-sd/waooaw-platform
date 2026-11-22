// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R007, WC149-R008, WC149-R009
// Constitutional basis: C-026, C-059, C-063, C-083

import { type NextRequest, NextResponse } from 'next/server';
import { proxyProviderConnections } from '@/lib/provider-connections-server';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';

type RouteContext = { params: Promise<{ path?: string[] }> };

const noStore = { 'Cache-Control': 'no-store' } as const;

async function handle(request: NextRequest, { params }: RouteContext) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) {
    return NextResponse.json(
      { code: 'CONNECTION_FORBIDDEN', title: 'Secure sign in is required.' },
      { status: 401, headers: noStore }
    );
  }
  if (request.method !== 'GET' && !isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin)) {
    return NextResponse.json(
      { code: 'CONNECTION_FORBIDDEN', title: 'Request origin is not allowed.' },
      { status: 403, headers: noStore }
    );
  }
  const { path } = await params;
  return proxyProviderConnections(request, accessToken, path ?? []);
}

export const GET = withServerFailureBoundary('web.provider_connections.get_failed', handle);
export const POST = withServerFailureBoundary('web.provider_connections.post_failed', handle);
