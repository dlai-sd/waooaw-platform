/** @jest-environment node */

jest.mock('@/lib/identity-security-events', () => ({ persistWebIdentitySecurityEvent: jest.fn() }));

import { NextRequest } from 'next/server';
import { persistWebIdentitySecurityEvent } from '@/lib/identity-security-events';
import { POST } from './route';

describe('identity security event BFF', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXTAUTH_URL = 'https://app.example';
    jest.mocked(persistWebIdentitySecurityEvent).mockResolvedValue(true);
  });

  it('maps a bounded same-origin transition without accepting arbitrary event fields', async () => {
    const correlationId = crypto.randomUUID();
    const response = await POST(new NextRequest('https://app.example/api/auth/identity-events', {
      method: 'POST',
      headers: { origin: 'https://app.example', 'content-type': 'application/json' },
      body: JSON.stringify({
        correlationId,
        stage: 'BROKER_REDIRECT_REQUESTED',
        providerClass: 'FACEBOOK',
        eventType: 'SESSION_REVOCATION_ALL',
      }),
    }));

    expect(response.status).toBe(204);
    expect(persistWebIdentitySecurityEvent).toHaveBeenCalledWith(expect.objectContaining({
      correlationId,
      eventType: 'PROVIDER_HANDOFF',
      providerClass: 'FACEBOOK',
      outcome: 'ATTEMPTED',
    }));
  });

  it('rejects cross-origin, malformed, and unsupported transitions', async () => {
    for (const [origin, body] of [
      ['https://attacker.example', { correlationId: crypto.randomUUID(), stage: 'SESSION_RESOLVED', providerClass: 'GOOGLE' }],
      ['https://app.example', { correlationId: 'not-a-uuid', stage: 'SESSION_RESOLVED', providerClass: 'GOOGLE' }],
      ['https://app.example', { correlationId: crypto.randomUUID(), stage: 'ARBITRARY', providerClass: 'GOOGLE' }],
    ] as const) {
      const response = await POST(new NextRequest('https://app.example/api/auth/identity-events', {
        method: 'POST', headers: { origin, 'content-type': 'application/json' }, body: JSON.stringify(body),
      }));
      expect(response.status).toBeGreaterThanOrEqual(400);
    }
    expect(persistWebIdentitySecurityEvent).not.toHaveBeenCalled();
  });

  it('returns a visible unavailable state when durable persistence fails', async () => {
    jest.mocked(persistWebIdentitySecurityEvent).mockRejectedValueOnce(new Error('unavailable'));
    const response = await POST(new NextRequest('https://app.example/api/auth/identity-events', {
      method: 'POST',
      headers: { origin: 'https://app.example', 'content-type': 'application/json' },
      body: JSON.stringify({ correlationId: crypto.randomUUID(), stage: 'CALLBACK_FAILED', providerClass: 'UNKNOWN' }),
    }));
    expect(response.status).toBe(503);
  });
});