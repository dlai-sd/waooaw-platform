// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R028, R032
// Constitutional basis: C-023, C-059, C-063, C-088

import { type NextRequest, NextResponse } from 'next/server';
import { proxyOperationAdmin } from '@/lib/api/operation-proxy';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';

type RouteContext = { params: Promise<{ path?: string[] }> };

const noStore = { 'Cache-Control': 'no-store' } as const;

async function handle(request: NextRequest, { params }: RouteContext) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken)
    return NextResponse.json(
      { code: 'OPERATION_ADMIN_FORBIDDEN', title: 'Secure sign in is required.' },
      { status: 401, headers: noStore }
    );
  if (request.method !== 'GET' && !isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin))
    return NextResponse.json(
      { code: 'OPERATION_ADMIN_FORBIDDEN', title: 'Request origin is not allowed.' },
      { status: 403, headers: noStore }
    );
  const { path } = await params;
  return proxyOperationAdmin(request, accessToken, path ?? []);
}

export const GET = withServerFailureBoundary('web.admin.agent_operation.get_failed', handle);
export const PUT = withServerFailureBoundary('web.admin.agent_operation.put_failed', handle);
