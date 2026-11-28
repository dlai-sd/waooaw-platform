// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-059, C-063, C-078

import { type NextRequest, NextResponse } from 'next/server';
import { customerDataRequestRoutes, proxyOversight } from '@/lib/oversight-proxy';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';

const noStore = { 'Cache-Control': 'no-store' } as const;

// The Business Platform decides who may ask (the account owner only); this route forwards the one collection.
async function handle(request: NextRequest) {
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
  return proxyOversight(request, accessToken, '/api/v1/customer-data-requests', customerDataRequestRoutes, []);
}

export const GET = withServerFailureBoundary('web.customer_data_requests.get_failed', handle);
export const POST = withServerFailureBoundary('web.customer_data_requests.post_failed', handle);
