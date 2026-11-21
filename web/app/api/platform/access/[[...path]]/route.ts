// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063

import { type NextRequest, NextResponse } from 'next/server';
import { proxyPlatformAccess } from '@/lib/platform-access-server';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';

type RouteContext = { params: Promise<{ path?: string[] }> };

const noStore = { 'Cache-Control': 'no-store' } as const;

async function handle(request: NextRequest, { params }: RouteContext) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) {
    return NextResponse.json(
      { code: 'PLATFORM_ACCESS_SIGN_IN_REQUIRED', title: 'Secure sign in is required.' },
      { status: 401, headers: noStore }
    );
  }
  if (request.method !== 'GET' && !isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin)) {
    return NextResponse.json(
      { code: 'PLATFORM_ACCESS_ORIGIN_DENIED', title: 'Request origin is not allowed.' },
      { status: 403, headers: noStore }
    );
  }
  const { path } = await params;
  return proxyPlatformAccess(request, accessToken, path ?? []);
}

export const GET = withServerFailureBoundary('web.platform_access.get_failed', handle);
export const POST = withServerFailureBoundary('web.platform_access.post_failed', handle);
