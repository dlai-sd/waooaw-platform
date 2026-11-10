/** @jest-environment node */

import { NextRequest, NextResponse } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { enforceAuthAbuse } from '@/lib/auth-abuse-limiter';
import { createIdentityApi } from '@/lib/api/identity';
import { IdentityApi } from '@/lib/api/generated/apis/IdentityApi';
import type { IdentityAccountLink } from '@/lib/api/generated/models/IdentityAccountLink';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { POST } from './route';

jest.mock('@/lib/auth', () => ({ activeAccessToken: jest.fn() }));
jest.mock('@/lib/auth-abuse-limiter', () => ({ enforceAuthAbuse: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ createIdentityApi: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ sessionTokenFromRequest: jest.fn() }));
jest.mock('@/lib/server-failure-boundary', () => ({
  readRequestJson: (request: Request) => request.json(),
  withServerFailureBoundary: (_event: string, handler: unknown) => handler,
}));

const key = '00000000-0000-4000-8000-000000000001';
const api = new IdentityApi();
const start = jest.spyOn(api, 'startIdentityAccountLink');
const approve = jest.spyOn(api, 'approveIdentityAccountLink');
const cancel = jest.spyOn(api, 'cancelIdentityAccountLink');
const status = jest.spyOn(api, 'getIdentityAccountLink');
const link: IdentityAccountLink = {
  linkId: key,
  state: 'PENDING_PORTAL_APPROVAL',
  requiredAssurance: 'AAL3_FRESH',
  maskedMobile: '***0100',
  expiresAt: new Date(),
  updatedAt: new Date(),
};

function request(body: unknown, origin = 'https://waooaw.test') {
  return new NextRequest('https://waooaw.test/api/identity/account-links', {
    method: 'POST',
    headers: { origin, 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

describe('WhatsApp account-link BFF', () => {
  const priorOrigin = process.env.NEXTAUTH_URL;
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXTAUTH_URL = 'https://waooaw.test';
    jest.mocked(enforceAuthAbuse).mockResolvedValue(null);
    jest.mocked(sessionTokenFromRequest).mockResolvedValue({});
    jest.mocked(activeAccessToken).mockReturnValue('synthetic-access-token');
    jest.mocked(createIdentityApi).mockReturnValue(api);
    start.mockResolvedValue(link);
    approve.mockResolvedValue(link);
    cancel.mockResolvedValue({ ...link, state: 'CANCELLED' });
    status.mockResolvedValue(link);
  });
  afterAll(() => {
    if (priorOrigin === undefined) Reflect.deleteProperty(process.env, 'NEXTAUTH_URL');
    else process.env.NEXTAUTH_URL = priorOrigin;
  });

  it('selects the proof server-side and returns a no-store response', async () => {
    const result = await POST(request({ command: 'START', idempotencyKey: key }));
    expect(result.status).toBe(200);
    expect(result.headers.get('cache-control')).toBe('no-store');
    expect(api.startIdentityAccountLink).toHaveBeenCalledWith(
      {
        idempotencyKey: key,
        startIdentityAccountLinkRequest: {},
      },
      { cache: 'no-store' }
    );
  });

  it.each(['APPROVE', 'CANCEL', 'STATUS'])(
    'routes an explicit %s command to the caller-bound operation',
    async (command) => {
      const result = await POST(request({ command, idempotencyKey: key, linkId: key }));
      expect(result.status).toBe(200);
      expect(
        command === 'APPROVE'
          ? api.approveIdentityAccountLink
          : command === 'CANCEL'
            ? api.cancelIdentityAccountLink
            : api.getIdentityAccountLink
      ).toHaveBeenCalled();
      expect(api.startIdentityAccountLink).not.toHaveBeenCalled();
    }
  );

  it('rejects cross-origin calls before session, limiter or backend access', async () => {
    const result = await POST(request({ command: 'START', idempotencyKey: key }, 'https://other.test'));
    expect(result.status).toBe(403);
    expect(enforceAuthAbuse).not.toHaveBeenCalled();
    expect(sessionTokenFromRequest).not.toHaveBeenCalled();
    expect(createIdentityApi).not.toHaveBeenCalled();
  });

  it('requires a current session and preserves the shared authority-change limiter', async () => {
    jest.mocked(enforceAuthAbuse).mockResolvedValueOnce(NextResponse.json({}, { status: 429 }));
    expect((await POST(request({ command: 'START', idempotencyKey: key }))).status).toBe(429);
    expect(createIdentityApi).not.toHaveBeenCalled();
    jest.mocked(activeAccessToken).mockReturnValue(undefined);
    expect((await POST(request({ command: 'START', idempotencyKey: key }))).status).toBe(401);
  });

  it.each([
    { command: 'START', mobile: '+14155550100', idempotencyKey: key },
    { command: 'START', verifiedMobileProofId: key, idempotencyKey: key },
    { command: 'APPROVE', linkId: 'invalid', idempotencyKey: key },
    { command: 'UNKNOWN', idempotencyKey: key },
  ])('rejects raw/client-selected authority and invalid commands', async (body) => {
    expect((await POST(request(body))).status).toBe(400);
    expect(createIdentityApi).not.toHaveBeenCalled();
  });
});
