import { logServerFailure } from '@/lib/server-failure';
import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { createIdentityApi } from '@/lib/api/identity';
import { ResponseError } from '@/lib/api/generated/runtime';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { rotateSessionMembership } from '@/lib/web-session-store';

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

async function POSTHandler(request: NextRequest) {
  const token = await sessionTokenFromRequest(request);
  const accessToken = token ? activeAccessToken(token) : undefined;
  if (!token || !accessToken)
    return NextResponse.json(
      { code: 'IDENTITY_SESSION_REQUIRED' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  const body = (await readRequestJson(request).catch(() => null)) as {
    membershipReference?: unknown;
    idempotencyKey?: unknown;
  } | null;
  if (
    !body ||
    typeof body.membershipReference !== 'string' ||
    !uuidPattern.test(body.membershipReference) ||
    typeof body.idempotencyKey !== 'string' ||
    !uuidPattern.test(body.idempotencyKey)
  )
    return NextResponse.json(
      { code: 'IDENTITY_REQUEST_INVALID' },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  try {
    const selection = await createIdentityApi(accessToken).validateIdentityMembershipSelection(
      {
        idempotencyKey: body.idempotencyKey,
        identityMembershipSelectionRequestV1: {
          schemaVersion: '1.0',
          membershipReference: body.membershipReference,
        },
      },
      { cache: 'no-store' }
    );
    const rotated = await rotateSessionMembership(token, selection.membership.membershipReference);
    if (!rotated || typeof rotated.sessionHandle !== 'string' || typeof rotated.sessionAbsoluteExpiresAt !== 'string')
      return NextResponse.json(
        { code: 'IDENTITY_SESSION_ROTATION_REQUIRED' },
        { status: 409, headers: { 'Cache-Control': 'no-store' } }
      );
    const response = NextResponse.json(selection, {
      headers: { 'Cache-Control': 'no-store' },
    });
    response.cookies.set('__Host-waooaw-session', rotated.sessionHandle, {
      expires: new Date(rotated.sessionAbsoluteExpiresAt),
      httpOnly: true,
      path: '/',
      sameSite: 'lax',
      secure: true,
    });
    return response;
  } catch (error) {
    logServerFailure('web.identity.membership.selection.request_failed', error);
    const status = error instanceof ResponseError && error.response.status >= 400 ? error.response.status : 503;
    return NextResponse.json(
      {
        code:
          status === 404
            ? 'IDENTITY_RESOURCE_NOT_ACCESSIBLE'
            : status === 409
              ? 'IDENTITY_MEMBERSHIP_INACTIVE'
              : 'IDENTITY_DEPENDENCY_UNAVAILABLE',
      },
      { status, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

export const POST = withServerFailureBoundary('web.identity.membership.selection.post_failed', POSTHandler);
