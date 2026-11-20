// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-04
// Constitutional basis: C-001, C-023, C-059, C-063, ADR-051

import { type NextRequest, NextResponse } from 'next/server';
import { proxyWorkbench } from '@/lib/api/workbench-proxy';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';

type RouteContext = { params: Promise<{ relationshipId: string; path?: string[] }> };

async function handle(request: NextRequest, { params }: RouteContext) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken)
    return NextResponse.json(
      { title: 'Secure sign in is required.' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  if (request.method === 'POST' && !isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin))
    return NextResponse.json(
      { code: 'WORKBENCH_REQUEST_INVALID', title: 'Request origin is not allowed.' },
      { status: 403, headers: { 'Cache-Control': 'no-store' } }
    );
  const { relationshipId, path } = await params;
  return proxyWorkbench(request, accessToken, relationshipId, path ?? []);
}

export const GET = withServerFailureBoundary('web.relationships.relationshipid.workbench.get_failed', handle);
export const POST = withServerFailureBoundary('web.relationships.relationshipid.workbench.post_failed', handle);
