import { type NextRequest, NextResponse } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { createIdentityApi } from '@/lib/api/identity';
import { ResponseError } from '@/lib/api/generated/runtime';
import { enforceAuthorityChangeRevocation } from '@/lib/identity-lifecycle';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { enforceAuthAbuse } from '@/lib/auth-abuse-limiter';

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function POST(request: NextRequest) {
  const limited = await enforceAuthAbuse(request, 'PROVIDER_LINK');
  if (limited) return limited;
  const token = await sessionTokenFromRequest(request);
  const accessToken = token ? activeAccessToken(token) : undefined;
  if (!token || !accessToken)
    return NextResponse.json(
      { code: 'IDENTITY_SESSION_REQUIRED' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  const body = (await request.json().catch(() => null)) as {
    provider?: unknown;
    stepUpTransactionReference?: unknown;
    idempotencyKey?: unknown;
  } | null;
  if (
    !body ||
    !['GOOGLE', 'FACEBOOK', 'APPLE', 'EMAIL'].includes(String(body.provider)) ||
    typeof body.stepUpTransactionReference !== 'string' ||
    !uuidPattern.test(body.stepUpTransactionReference) ||
    typeof body.idempotencyKey !== 'string' ||
    !uuidPattern.test(body.idempotencyKey)
  )
    return NextResponse.json(
      { code: 'IDENTITY_REQUEST_INVALID' },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  try {
    const operation = await createIdentityApi(accessToken).createIdentityProviderLink(
      {
        idempotencyKey: body.idempotencyKey,
        identityProviderLinkRequestV1: {
          schemaVersion: '1.0',
          provider: body.provider as 'GOOGLE' | 'FACEBOOK' | 'APPLE' | 'EMAIL',
          stepUpTransactionReference: body.stepUpTransactionReference,
        },
      },
      { cache: 'no-store' }
    );
    const revoked = await enforceAuthorityChangeRevocation(operation, token, accessToken, body.idempotencyKey);
    const response = NextResponse.json(operation, {
      status: 202,
      headers: { 'Cache-Control': 'no-store' },
    });
    if (revoked)
      response.cookies.set('__Host-waooaw-session', '', {
        httpOnly: true,
        maxAge: 0,
        path: '/',
        sameSite: 'lax',
        secure: true,
      });
    return response;
  } catch (error) {
    const status = error instanceof ResponseError && error.response.status >= 400 ? error.response.status : 503;
    return NextResponse.json(
      {
        code:
          status === 403
            ? 'IDENTITY_STEP_UP_REQUIRED'
            : status === 409
              ? 'IDENTITY_ACTION_DENIED'
              : 'IDENTITY_DEPENDENCY_UNAVAILABLE',
      },
      { status, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}
