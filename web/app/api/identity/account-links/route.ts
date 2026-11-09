// Implements: WC-134 R005; identity-boundary.md Section 6.3.
// Constitutional basis: C-023, C-026, C-059, C-063

import { type NextRequest, NextResponse } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { enforceAuthAbuse } from '@/lib/auth-abuse-limiter';
import { createIdentityApi } from '@/lib/api/identity';
import { ResponseError } from '@/lib/api/generated/runtime';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { logServerFailure } from '@/lib/server-failure';
import { readRequestJson, withServerFailureBoundary } from '@/lib/server-failure-boundary';

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const headers = { 'Cache-Control': 'no-store' };

function problem(status: number, code: string) {
  return NextResponse.json({ code }, { status, headers });
}

async function POSTHandler(request: NextRequest) {
  if (!isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin))
    return problem(403, 'IDENTITY_ACTION_DENIED');
  const limited = await enforceAuthAbuse(request, 'PROVIDER_LINK');
  if (limited) return limited;
  const session = await sessionTokenFromRequest(request);
  const accessToken = session ? activeAccessToken(session) : undefined;
  if (!accessToken) return problem(401, 'IDENTITY_SESSION_REQUIRED');
  const body = await readRequestJson(request);
  if (
    body === null ||
    typeof body !== 'object' ||
    !('command' in body) ||
    !['START', 'APPROVE', 'CANCEL', 'STATUS'].includes(String(body.command)) ||
    !('idempotencyKey' in body) ||
    typeof body.idempotencyKey !== 'string' ||
    !uuid.test(body.idempotencyKey) ||
    Object.keys(body).some((key) => !['command', 'idempotencyKey', 'linkId'].includes(key))
  )
    return problem(400, 'IDENTITY_REQUEST_INVALID');
  const linkId = 'linkId' in body ? body.linkId : undefined;
  if (body.command !== 'START' && (typeof linkId !== 'string' || !uuid.test(linkId)))
    return problem(400, 'IDENTITY_REQUEST_INVALID');
  try {
    const api = createIdentityApi(accessToken);
    const result =
      body.command === 'START'
        ? await api.startIdentityAccountLink(
            {
              idempotencyKey: body.idempotencyKey,
              startIdentityAccountLinkRequest: {},
            },
            { cache: 'no-store' }
          )
        : body.command === 'APPROVE'
          ? await api.approveIdentityAccountLink(
              {
                linkId: String(linkId),
                idempotencyKey: body.idempotencyKey,
              },
              { cache: 'no-store' }
            )
          : body.command === 'CANCEL'
            ? await api.cancelIdentityAccountLink(
                { linkId: String(linkId), idempotencyKey: body.idempotencyKey },
                { cache: 'no-store' }
              )
            : await api.getIdentityAccountLink({ linkId: String(linkId) }, { cache: 'no-store' });
    return NextResponse.json(result, { headers });
  } catch (error) {
    logServerFailure('web.identity.account_links.owner_failed', error);
    if (!(error instanceof ResponseError)) throw error;
    const status = error.response.status;
    const codes: Record<number, string> = {
      400: 'IDENTITY_REQUEST_INVALID',
      401: 'IDENTITY_SESSION_REQUIRED',
      403: 'IDENTITY_ACTION_DENIED',
      404: 'IDENTITY_RESOURCE_NOT_ACCESSIBLE',
      409: 'IDENTITY_IDEMPOTENCY_CONFLICT',
      410: 'IDENTITY_CHALLENGE_EXPIRED',
      429: 'IDENTITY_RATE_LIMITED',
      503: 'IDENTITY_DEPENDENCY_UNAVAILABLE',
    };
    if (status === 403) {
      const body: unknown = await error.response.json();
      if (body !== null && typeof body === 'object' && 'code' in body && body.code === 'IDENTITY_STEP_UP_REQUIRED')
        return problem(403, 'IDENTITY_STEP_UP_REQUIRED');
    }
    return problem(status in codes ? status : 503, codes[status] ?? 'IDENTITY_DEPENDENCY_UNAVAILABLE');
  }
}

export const POST = withServerFailureBoundary('web.identity.account_links.request_failed', POSTHandler);
