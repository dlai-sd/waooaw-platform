/** @jest-environment node */

import { persistAcquisitionIntent } from '@/lib/api/acquisition-intent';
import { getIdentitySession } from '@/lib/api/identity';
import { createMyAgentsSelection } from '@/lib/api/my-agents-selection';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { NextRequest } from 'next/server';

const continueAcquisition = jest.fn();

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/api/acquisition-intent', () => ({ persistAcquisitionIntent: jest.fn() }));
jest.mock('@/lib/api/my-agents-selection', () => ({
  createMyAgentsSelection: jest.fn(),
  myAgentsSelectionCookie: 'waooaw_my_agents_selection',
}));
jest.mock('@/lib/api/generated/apis/ProfessionalsApi', () => ({
  ProfessionalsApi: jest.fn(() => ({ continueAcquisition })),
}));

function request() {
  return new NextRequest('http://localhost/api/acquisition/continue', {
    method: 'POST',
    body: JSON.stringify({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      professionalVersion: '1.0.0',
      intent: 'trial',
      disclosureRevision: '1.0.0',
      termsVersion: '2026-07-18',
      idempotencyKey: '11111111-1111-4111-8111-111111111111',
      contractAcceptance: 'ACCEPT_EMPLOYMENT_CONTRACT',
    }),
  });
}

describe('acquisition continuation identity boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
    jest
      .mocked(persistAcquisitionIntent)
      .mockResolvedValue(new Response('{}', { status: 201, headers: { 'Content-Type': 'application/json' } }));
    jest.mocked(createMyAgentsSelection).mockResolvedValue({
      handle: 'a'.repeat(64),
      expiresAt: '2026-09-28T12:05:00.000Z',
    });
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
    expect(persistAcquisitionIntent).toHaveBeenCalledWith(
      'access-token',
      '11111111-1111-4111-8111-111111111111',
      expect.objectContaining({ intent: 'TRIAL', professionalVersion: '1.0.0' })
    );
    expect(continueAcquisition).not.toHaveBeenCalled();
  });

  it('rejects Trial continuation without explicit Employment Contract acceptance', async () => {
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'ready', session: {} as never });
    const { POST } = await import('./route');
    const invalid = new NextRequest('http://localhost/api/acquisition/continue', {
      method: 'POST',
      body: JSON.stringify({
        professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
        professionalVersion: '1.0.0',
        intent: 'trial',
        disclosureRevision: '1.0.0',
        termsVersion: '2026-07-18',
        idempotencyKey: '11111111-1111-4111-8111-111111111111',
      }),
    });

    expect((await POST(invalid)).status).toBe(400);
    expect(continueAcquisition).not.toHaveBeenCalled();
  });

  it('forwards acquisition only for a ready customer identity', async () => {
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'ready', session: {} as never });
    continueAcquisition.mockResolvedValue({
      relationshipId: '22222222-2222-4222-8222-222222222222',
      resumePath: '/relationships/22222222-2222-4222-8222-222222222222',
    });
    const { POST } = await import('./route');

    const response = await POST(request());
    expect(response.status).toBe(200);
    expect(continueAcquisition).toHaveBeenCalledTimes(1);
    expect(createMyAgentsSelection).toHaveBeenCalledWith(
      'access-token',
      '22222222-2222-4222-8222-222222222222',
      'TRIAL_STARTED'
    );
    expect(await response.json()).toEqual(expect.objectContaining({ resumePath: '/professionals/mine' }));
    expect(response.headers.get('set-cookie')).toEqual(
      expect.stringMatching(
        /^waooaw_my_agents_selection=[a-f0-9]{64};.*Path=\/professionals\/mine;.*Expires=.*Secure;.*HttpOnly;.*SameSite=strict$/i
      )
    );
  });

  it('does not confirm relationship HTTP success when authoritative selection creation fails', async () => {
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'ready', session: {} as never });
    continueAcquisition.mockResolvedValue({
      relationshipId: '22222222-2222-4222-8222-222222222222',
      resumePath: '/relationships/22222222-2222-4222-8222-222222222222',
    });
    jest.mocked(createMyAgentsSelection).mockRejectedValue(new Error('authoritative state unavailable'));
    const { POST } = await import('./route');

    const response = await POST(request());

    expect(response.status).toBe(503);
    expect(response.headers.get('set-cookie')).toBeNull();
  });
});
