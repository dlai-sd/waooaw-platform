/** @jest-environment node */

import { NextRequest } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { createIdentityApi } from '@/lib/api/identity';
import { IdentityApi } from '@/lib/api/generated/apis/IdentityApi';
import { JSONApiResponse, ResponseError } from '@/lib/api/generated/runtime';
import type { IdentityPhoneChangeV1 } from '@/lib/api/generated/models/IdentityPhoneChangeV1';
import { enforceAuthAbuse } from '@/lib/auth-abuse-limiter';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { POST } from './route';

jest.mock('@/lib/auth', () => ({ activeAccessToken: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ createIdentityApi: jest.fn() }));
jest.mock('@/lib/auth-abuse-limiter', () => ({ enforceAuthAbuse: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ sessionTokenFromRequest: jest.fn() }));
jest.mock('@/lib/server-failure-boundary', () => ({
  readRequestJson: (request: Request) => request.json(),
  withServerFailureBoundary: (_event: string, handler: unknown) => handler,
}));

const key = '00000000-0000-4000-8000-000000000001';
const api = new IdentityApi();
const start = jest.spyOn(api, 'startIdentityPhoneChange');
const confirm = jest.spyOn(api, 'confirmIdentityPhoneChange');
const cancel = jest.spyOn(api, 'cancelIdentityPhoneChange');
const status = jest.spyOn(api, 'getIdentityPhoneChangeRaw');
const pending: IdentityPhoneChangeV1 = {
  challengeId: key,
  state: 'OTP_REQUIRED',
  maskedMobile: '***0100',
  expiresAt: new Date(),
  relationshipApprovalRequired: true,
};
const body = { command: 'START', idempotencyKey: key, mobile: '+14155550100' };
const request = (value: unknown, origin = 'https://waooaw.test') =>
  new NextRequest('https://waooaw.test/api/identity/phone-changes', {
    method: 'POST',
    headers: { origin, 'content-type': 'application/json' },
    body: JSON.stringify(value),
  });

describe('Phone-change BFF', () => {
  const oldOrigin = process.env.NEXTAUTH_URL;
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXTAUTH_URL = 'https://waooaw.test';
    jest.mocked(activeAccessToken).mockReturnValue('synthetic-access');
    jest.mocked(enforceAuthAbuse).mockResolvedValue(null);
    jest.mocked(sessionTokenFromRequest).mockResolvedValue({});
    jest.mocked(createIdentityApi).mockReturnValue(api);
    start.mockResolvedValue(pending);
    confirm.mockResolvedValue({ ...pending, state: 'COMPLETED' });
    cancel.mockResolvedValue({ ...pending, state: 'EXPIRED' });
    status.mockResolvedValue(new JSONApiResponse(new Response(JSON.stringify(pending)), () => pending));
  });
  afterAll(() => {
    if (oldOrigin === undefined) Reflect.deleteProperty(process.env, 'NEXTAUTH_URL');
    else process.env.NEXTAUTH_URL = oldOrigin;
  });

  it('binds new number verification to current server authentication and returns no-store', async () => {
    const result = await POST(request(body));
    expect(result.status).toBe(200);
    expect(result.headers.get('cache-control')).toBe('no-store');
    expect(start).toHaveBeenCalledWith(
      {
        idempotencyKey: key,
        startIdentityPhoneChangeRequestV1: { mobile: body.mobile },
      },
      { cache: 'no-store' }
    );
    expect(createIdentityApi).toHaveBeenCalledWith('synthetic-access');
  });

  it('requires OTP plus explicit consent and uses the owning confirm endpoint', async () => {
    const result = await POST(
      request({
        command: 'CONFIRM',
        idempotencyKey: key,
        challengeId: key,
        code: '123456',
        consent: true,
      })
    );
    expect(result.status).toBe(200);
    expect(confirm).toHaveBeenCalledWith(
      {
        idempotencyKey: key,
        confirmIdentityPhoneChangeRequestV1: {
          challengeId: key,
          code: '123456',
          consent: true,
        },
      },
      { cache: 'no-store' }
    );
    expect(start).not.toHaveBeenCalled();
  });

  it('supports cancel and recovery without implicitly resending OTP', async () => {
    await POST(request({ command: 'CANCEL', idempotencyKey: key, challengeId: key }));
    expect(cancel).toHaveBeenCalledWith({ idempotencyKey: key, challengeId: key }, { cache: 'no-store' });
    status.mockResolvedValueOnce(new JSONApiResponse(new Response(null, { status: 204 }), () => pending));
    const empty = await POST(request({ command: 'STATUS' }));
    expect(empty.status).toBe(204);
    expect(empty.headers.get('cache-control')).toBe('no-store');
    expect(status).toHaveBeenCalledWith({ cache: 'no-store' });
    expect(start).not.toHaveBeenCalled();
  });

  it('rejects cross-origin and missing-session calls before backend access', async () => {
    expect((await POST(request(body, 'https://foreign.test'))).status).toBe(403);
    expect(enforceAuthAbuse).not.toHaveBeenCalled();
    jest.mocked(activeAccessToken).mockReturnValue(undefined);
    expect((await POST(request(body))).status).toBe(401);
    expect(createIdentityApi).not.toHaveBeenCalled();
  });

  it.each([
    { ...body, tenantId: key },
    { ...body, accountId: key },
    { ...body, oldNumber: '+14155550000' },
    { ...body, mobile: '14155550100' },
    { ...body, command: 'REASSIGN' },
    {
      command: 'CONFIRM',
      idempotencyKey: key,
      challengeId: key,
      code: '123456',
      consent: false,
    },
    {
      command: 'CONFIRM',
      idempotencyKey: key,
      challengeId: key,
      code: '123',
      consent: true,
    },
    { command: 'STATUS', mobile: body.mobile },
  ])('rejects invalid or client-supplied authority', async (value) => {
    expect((await POST(request(value))).status).toBe(400);
    expect(createIdentityApi).not.toHaveBeenCalled();
  });

  it('preserves step-up without leaking backend error details', async () => {
    start.mockRejectedValueOnce(
      new ResponseError(
        new Response(
          JSON.stringify({
            code: 'IDENTITY_STEP_UP_REQUIRED',
            secret: 'synthetic',
          }),
          { status: 403 }
        )
      )
    );
    const result = await POST(request(body));
    expect(await result.json()).toEqual({ code: 'IDENTITY_STEP_UP_REQUIRED' });
  });
});
