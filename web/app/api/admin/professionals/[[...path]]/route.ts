// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R024
// Constitutional basis: C-023, C-059, C-063, C-088

import { type NextRequest, NextResponse } from 'next/server';
import { proxyProfessionalApprovals } from '@/lib/api/professional-approvals-proxy';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';

type RouteContext = { params: Promise<{ path?: string[] }> };

const noStore = { 'Cache-Control': 'no-store' } as const;

async function handle(request: NextRequest, { params }: RouteContext) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken)
    return NextResponse.json(
      { code: 'PROFESSIONAL_APPROVAL_FORBIDDEN', title: 'Secure sign in is required.' },
      { status: 401, headers: noStore }
    );
  if (request.method !== 'GET' && !isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin))
    return NextResponse.json(
      { code: 'PROFESSIONAL_APPROVAL_FORBIDDEN', title: 'Request origin is not allowed.' },
      { status: 403, headers: noStore }
    );
  const { path } = await params;
  return proxyProfessionalApprovals(request, accessToken, path ?? []);
}

export const GET = withServerFailureBoundary('web.admin.professionals.get_failed', handle);
export const POST = withServerFailureBoundary('web.admin.professionals.post_failed', handle);
