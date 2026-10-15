/** @jest-environment node */

import { NextRequest } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { createIdentityApi } from '@/lib/api/identity';
import { POST } from '@/app/api/identity/membership-selection/route';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { rotateSessionMembership } from '@/lib/web-session-store';

jest.mock('@/lib/auth', () => ({ activeAccessToken: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ createIdentityApi: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ sessionTokenFromRequest: jest.fn() }));
jest.mock('@/lib/web-session-store', () => ({
  rotateSessionMembership: jest.fn(),
}));

const membershipReference = '11111111-1111-4111-8111-111111111111';
const idempotencyKey = '22222222-2222-4222-8222-222222222222';
const sessionToken = {
  sessionHandle: 'old-handle',
  sessionFamilyId: '33333333-3333-4333-8333-333333333333',
  sessionHandleId: '44444444-4444-4444-8444-444444444444',
  sessionAbsoluteExpiresAt: '2026-10-14T20:00:00.000Z',
  refreshVersion: 2,
};

function request() {
  return new NextRequest('https://cp.demo.waooaw.com/api/identity/membership-selection', {
    method: 'POST',
    body: JSON.stringify({ membershipReference, idempotencyKey }),
    headers: { 'content-type': 'application/json' },
  });
}

describe('membership selection BFF', () => {
  const validateIdentityMembershipSelection = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(sessionTokenFromRequest).mockResolvedValue(sessionToken as never);
    jest.mocked(activeAccessToken).mockReturnValue('server-access-token');
    jest.mocked(createIdentityApi).mockReturnValue({
      validateIdentityMembershipSelection,
    } as never);
    validateIdentityMembershipSelection.mockResolvedValue({
      schemaVersion: '1.0',
      membership: {
        membershipReference,
        tenantReference: '55555555-5555-4555-8555-555555555555',
        role: 'MANAGER',
        state: 'ACTIVE',
        selectionEligible: true,
      },
      validatedAt: new Date('2026-10-14T15:00:00Z'),
    });
  });

  it('rotates only after BP validates current membership', async () => {
    jest.mocked(rotateSessionMembership).mockResolvedValue({
      ...sessionToken,
      sessionHandle: 'new-opaque-handle',
      sessionHandleId: '66666666-6666-4666-8666-666666666666',
      refreshVersion: 3,
      activeMembershipId: membershipReference,
    } as never);

    const response = await POST(request());

    expect(response.status).toBe(200);
    expect(validateIdentityMembershipSelection).toHaveBeenCalled();
    expect(rotateSessionMembership).toHaveBeenCalledWith(sessionToken, membershipReference);
    expect(response.headers.get('set-cookie')).toContain('__Host-waooaw-session=new-opaque-handle');
  });

  it('preserves the existing handle when membership validation fails', async () => {
    validateIdentityMembershipSelection.mockRejectedValueOnce(new Error('membership unavailable'));

    const response = await POST(request());

    expect(response.status).toBe(503);
    expect(rotateSessionMembership).not.toHaveBeenCalled();
    expect(response.headers.get('set-cookie')).toBeNull();
  });

  it('issues no cookie when the atomic rotation loses a race', async () => {
    jest.mocked(rotateSessionMembership).mockResolvedValue(null);

    const response = await POST(request());

    expect(response.status).toBe(409);
    expect(response.headers.get('set-cookie')).toBeNull();
  });
});
