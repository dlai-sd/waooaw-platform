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
const problem = (status: number, code: string) => NextResponse.json({ code }, { status, headers });

async function POSTHandler(request: NextRequest) {
  if (!isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin))
    return problem(403, 'IDENTITY_ACTION_DENIED');
  const limited = await enforceAuthAbuse(request, 'PROVIDER_LINK');
  if (limited) return limited;
  const session = await sessionTokenFromRequest(request);
  const token = session ? activeAccessToken(session) : undefined;
  if (!token) return problem(401, 'IDENTITY_SESSION_REQUIRED');
  const body = await readRequestJson(request);
  if (body === null || typeof body !== 'object' || !('command' in body))
    return problem(400, 'IDENTITY_REQUEST_INVALID');
  const command = body.command;
  const fields =
    command === 'START'
      ? ['command', 'idempotencyKey', 'mobile']
      : command === 'CONFIRM'
        ? ['command', 'idempotencyKey', 'challengeId', 'code', 'consent']
        : command === 'CANCEL'
          ? ['command', 'idempotencyKey', 'challengeId']
          : command === 'STATUS'
            ? ['command']
            : undefined;
  if (!fields || Object.keys(body).some((field) => !fields.includes(field)))
    return problem(400, 'IDENTITY_REQUEST_INVALID');
  if (
    command !== 'STATUS' &&
    (!('idempotencyKey' in body) || typeof body.idempotencyKey !== 'string' || !uuid.test(body.idempotencyKey))
  )
    return problem(400, 'IDENTITY_REQUEST_INVALID');
  if (
    command === 'START' &&
    (!('mobile' in body) || typeof body.mobile !== 'string' || !/^\+[1-9][0-9]{7,14}$/.test(body.mobile))
  )
    return problem(400, 'IDENTITY_REQUEST_INVALID');
  if (
    (command === 'CONFIRM' || command === 'CANCEL') &&
    (!('challengeId' in body) || typeof body.challengeId !== 'string' || !uuid.test(body.challengeId))
  )
    return problem(400, 'IDENTITY_REQUEST_INVALID');
  if (
    command === 'CONFIRM' &&
    (!('consent' in body) ||
      body.consent !== true ||
      !('code' in body) ||
      typeof body.code !== 'string' ||
      !/^[0-9]{6}$/.test(body.code))
  )
    return problem(400, 'IDENTITY_REQUEST_INVALID');
  try {
    const api = createIdentityApi(token);
    if (command === 'STATUS') {
      const response = await api.getIdentityPhoneChangeRaw({
        cache: 'no-store',
      });
      if (response.raw.status === 204) return new NextResponse(null, { status: 204, headers });
      return NextResponse.json(await response.value(), { headers });
    }
    const key = String('idempotencyKey' in body ? body.idempotencyKey : '');
    const result =
      command === 'START'
        ? await api.startIdentityPhoneChange(
            {
              idempotencyKey: key,
              startIdentityPhoneChangeRequestV1: {
                mobile: String('mobile' in body ? body.mobile : ''),
              },
            },
            { cache: 'no-store' }
          )
        : command === 'CONFIRM'
          ? await api.confirmIdentityPhoneChange(
              {
                idempotencyKey: key,
                confirmIdentityPhoneChangeRequestV1: {
                  challengeId: String('challengeId' in body ? body.challengeId : ''),
                  code: String('code' in body ? body.code : ''),
                  consent: true,
                },
              },
              { cache: 'no-store' }
            )
          : await api.cancelIdentityPhoneChange(
              {
                idempotencyKey: key,
                challengeId: String('challengeId' in body ? body.challengeId : ''),
              },
              { cache: 'no-store' }
            );
    return NextResponse.json(result, { headers });
  } catch (error) {
    logServerFailure('web.identity.phone_changes.owner_failed', error);
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
      const failure: unknown = await error.response.json();
      if (
        failure !== null &&
        typeof failure === 'object' &&
        'code' in failure &&
        failure.code === 'IDENTITY_STEP_UP_REQUIRED'
      )
        return problem(403, 'IDENTITY_STEP_UP_REQUIRED');
    }
    return problem(status in codes ? status : 503, codes[status] ?? 'IDENTITY_DEPENDENCY_UNAVAILABLE');
  }
}

export const POST = withServerFailureBoundary('web.identity.phone_changes.request_failed', POSTHandler);
