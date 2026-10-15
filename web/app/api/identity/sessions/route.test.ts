/** @jest-environment node */

import { NextRequest } from 'next/server';
import { GET, DELETE } from './route';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { listSessions, revokeAllSessions } from '@/lib/web-session-store';

jest.mock('@/lib/server-auth', () => ({ sessionTokenFromRequest: jest.fn() }));
jest.mock('@/lib/web-session-store', () => ({
  listSessions: jest.fn(),
  revokeAllSessions: jest.fn(),
}));

const token = {
  globalUserId: '11111111-1111-4111-8111-111111111111',
  sessionFamilyId: '22222222-2222-4222-8222-222222222222',
};

function request(method: 'GET' | 'DELETE') {
  return new NextRequest('https://app.example/api/identity/sessions', {
    method,
    headers: method === 'DELETE' ? { 'Idempotency-Key': crypto.randomUUID() } : {},
  });
}

describe('Web-owned session collection route', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(sessionTokenFromRequest).mockResolvedValue(token as never);
  });

  it('requires a valid opaque Web session', async () => {
    jest.mocked(sessionTokenFromRequest).mockResolvedValue(null);

    expect((await GET(request('GET'))).status).toBe(401);
    expect(listSessions).not.toHaveBeenCalled();
  });

  it('lists only sessions returned for the authenticated global user', async () => {
    const sessions = [
      {
        sessionId: '33333333-3333-4333-8333-333333333333',
        issuedAt: new Date('2026-10-14T10:00:00Z'),
        lastSeenAt: new Date('2026-10-14T11:00:00Z'),
        expiresAt: new Date('2026-10-14T18:00:00Z'),
        assuranceLevel: 'AAL2_ACCOUNT',
        provider: 'UNKNOWN',
        deviceLabel: 'Current browser',
        current: true,
      },
    ];
    jest.mocked(listSessions).mockResolvedValue(sessions as never);

    const response = await GET(request('GET'));

    expect(response.status).toBe(200);
    expect(listSessions).toHaveBeenCalledWith(token);
    expect((await response.json()).sessions).toEqual([
      expect.objectContaining({
        sessionId: sessions[0].sessionId,
        current: true,
      }),
    ]);
  });

  it('returns a typed unavailable response when listing cannot be confirmed', async () => {
    jest.mocked(listSessions).mockRejectedValue(new Error('store unavailable'));

    const response = await GET(request('GET'));

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      code: 'SESSION_STORE_UNAVAILABLE',
      title: 'Session management is temporarily unavailable.',
    });
  });

  it('returns the truthful revoke-all count', async () => {
    jest.mocked(revokeAllSessions).mockResolvedValue(3);

    const response = await DELETE(request('DELETE'));

    expect(response.status).toBe(200);
    expect(revokeAllSessions).toHaveBeenCalledWith(token, 'CUSTOMER_REVOKED_ALL');
    expect(await response.json()).toEqual({ scope: 'ALL', revokedCount: 3 });
  });
});
