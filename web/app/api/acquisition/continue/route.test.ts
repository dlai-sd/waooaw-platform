/** @jest-environment node */

import { NextRequest } from 'next/server';
import { getIdentitySession } from '@/lib/api/identity';
import { accessTokenFromRequest } from '@/lib/server-auth';

const continueAcquisition = jest.fn();

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/api/generated/apis/ProfessionalsApi', () => ({
  ProfessionalsApi: jest.fn(() => ({ continueAcquisition })),
}));

function request() {
  return new NextRequest('http://localhost/api/acquisition/continue', {
    method: 'POST',
    body: JSON.stringify({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      professionalVersion: '1.0.0',
      intent: 'hire',
      disclosureRevision: '1.0.0',
      termsVersion: '2026-07-18',
      idempotencyKey: '11111111-1111-4111-8111-111111111111',
    }),
  });
}

describe('acquisition continuation identity boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
  });

  it('does not call acquisition without a secure session', async () => {
    jest.mocked(accessTokenFromRequest).mockResolvedValue(undefined);
    const { POST } = await import('./route');

    expect((await POST(request())).status).toBe(401);
    expect(getIdentitySession).not.toHaveBeenCalled();
    expect(continueAcquisition).not.toHaveBeenCalled();
  });

  it('does not call acquisition before customer registration', async () => {
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'registration-required' });
    const { POST } = await import('./route');

    const response = await POST(request());
    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({
      code: 'REGISTRATION_REQUIRED',
      title: 'Complete registration before starting a professional.',
    });
    expect(continueAcquisition).not.toHaveBeenCalled();
  });

  it('forwards acquisition only for a ready customer identity', async () => {
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'ready', session: {} as never });
    continueAcquisition.mockResolvedValue({ resumePath: '/relationships/relationship-1' });
    const { POST } = await import('./route');

    const response = await POST(request());
    expect(response.status).toBe(200);
    expect(continueAcquisition).toHaveBeenCalledTimes(1);
  });
});