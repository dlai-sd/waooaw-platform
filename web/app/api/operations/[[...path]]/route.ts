// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009, WC171-R010
// Constitutional basis: C-001, C-023, C-059, C-063

import { type NextRequest, NextResponse } from 'next/server';
import { operationsRoutes, proxyOversight } from '@/lib/oversight-proxy';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';

type RouteContext = { params: Promise<{ path?: string[] }> };

const noStore = { 'Cache-Control': 'no-store' } as const;

// The Business Platform decides who may read or resolve; this route only forwards the allow-listed operations.
async function handle(request: NextRequest, { params }: RouteContext) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken)
    return NextResponse.json(
      { code: 'SIGN_IN_REQUIRED', title: 'Secure sign in is required.' },
      { status: 401, headers: noStore }
    );
  if (request.method !== 'GET' && !isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin))
    return NextResponse.json(
      { code: 'ORIGIN_DENIED', title: 'Request origin is not allowed.' },
      { status: 403, headers: noStore }
    );
  const { path } = await params;
  return proxyOversight(request, accessToken, '/api/v1/operations', operationsRoutes, path ?? []);
}

export const GET = withServerFailureBoundary('web.operations.get_failed', handle);
export const POST = withServerFailureBoundary('web.operations.post_failed', handle);
