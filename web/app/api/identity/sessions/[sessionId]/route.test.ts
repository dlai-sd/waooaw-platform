/** @jest-environment node */

import { NextRequest } from 'next/server';
import { DELETE } from './route';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { revokeOneSession } from '@/lib/web-session-store';

jest.mock('@/lib/server-auth', () => ({ sessionTokenFromRequest: jest.fn() }));
jest.mock('@/lib/web-session-store', () => ({ revokeOneSession: jest.fn() }));

const token = {
  globalUserId: '11111111-1111-4111-8111-111111111111',
  sessionFamilyId: '22222222-2222-4222-8222-222222222222',
};
const sessionId = '33333333-3333-4333-8333-333333333333';

function request() {
  return new NextRequest(`https://app.example/api/identity/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: { 'Idempotency-Key': crypto.randomUUID() },
  });
}

describe('Web-owned single-session route', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(sessionTokenFromRequest).mockResolvedValue(token as never);
  });

  it('requires a valid opaque Web session', async () => {
    jest.mocked(sessionTokenFromRequest).mockResolvedValue(null);

    const response = await DELETE(request(), {
      params: Promise.resolve({ sessionId }),
    });

    expect(response.status).toBe(401);
    expect(revokeOneSession).not.toHaveBeenCalled();
  });

  it('passes the authenticated user and opaque handle reference to the store', async () => {
    jest.mocked(revokeOneSession).mockResolvedValue(1);

    const response = await DELETE(request(), {
      params: Promise.resolve({ sessionId }),
    });

    expect(response.status).toBe(200);
    expect(revokeOneSession).toHaveBeenCalledWith(token, sessionId);
    expect(await response.json()).toEqual({ scope: 'ONE', revokedCount: 1 });
  });

  it('does not claim revocation for an inaccessible handle', async () => {
    jest.mocked(revokeOneSession).mockResolvedValue(-1);

    const response = await DELETE(request(), {
      params: Promise.resolve({ sessionId }),
    });

    expect(response.status).toBe(404);
  });

  it('returns a typed unavailable response when revocation cannot be confirmed', async () => {
    jest.mocked(revokeOneSession).mockRejectedValue(new Error('store unavailable'));

    const response = await DELETE(request(), {
      params: Promise.resolve({ sessionId }),
    });

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      code: 'SESSION_STORE_UNAVAILABLE',
      title: 'Session revocation could not be confirmed.',
      correlationId: response.headers.get('x-correlation-id'),
    });
  });
});
