// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R030
// Constitutional basis: C-001, C-023, C-059, C-063

import { type NextRequest, NextResponse } from 'next/server';
import { proxyOperation } from '@/lib/api/operation-proxy';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';

type RouteContext = { params: Promise<{ relationshipId: string; path?: string[] }> };

const noStore = { 'Cache-Control': 'no-store' } as const;

async function handle(request: NextRequest, { params }: RouteContext) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken)
    return NextResponse.json(
      { code: 'OPERATION_SIGN_IN_REQUIRED', title: 'Secure sign in is required.' },
      { status: 401, headers: noStore }
    );
  if (request.method !== 'GET' && !isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin))
    return NextResponse.json(
      { code: 'OPERATION_REQUEST_INVALID', title: 'Request origin is not allowed.' },
      { status: 403, headers: noStore }
    );
  const { relationshipId, path } = await params;
  return proxyOperation(request, accessToken, relationshipId, path ?? []);
}

export const GET = withServerFailureBoundary('web.relationships.relationshipid.operation.get_failed', handle);
export const POST = withServerFailureBoundary('web.relationships.relationshipid.operation.post_failed', handle);
export const PUT = withServerFailureBoundary('web.relationships.relationshipid.operation.put_failed', handle);
export const PATCH = withServerFailureBoundary('web.relationships.relationshipid.operation.patch_failed', handle);
