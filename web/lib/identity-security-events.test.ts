/** @jest-environment node */

import { createHmac } from 'node:crypto';
import { persistWebIdentitySecurityEvent } from './identity-security-events';

const signingKey = 'test-only-identity-event-signing-key-32-bytes';

describe('identity security event transport', () => {
  beforeEach(() => {
    process.env.IDENTITY_EVENT_SIGNING_KEY = signingKey;
    process.env.BUSINESS_PLATFORM_URL = 'https://business.example';
  });

  afterEach(() => {
    jest.restoreAllMocks();
    Reflect.deleteProperty(globalThis, 'fetch');
  });

  it('signs the exact privacy-safe body sent to Business Platform', async () => {
    const request = jest.fn().mockResolvedValue(new Response(null, { status: 201 }));
    Object.defineProperty(globalThis, 'fetch', { configurable: true, value: request });

    await expect(
      persistWebIdentitySecurityEvent({
        correlationId: '64afc112-02a2-47ba-b87f-5296bb0cf703',
        sourceEventId: 'web:callback-1',
        eventType: 'CALLBACK_SUCCESS',
        providerClass: 'GOOGLE',
        outcome: 'SUCCEEDED',
        reasonCode: 'BROKER_CALLBACK_VALID',
        assuranceClass: 'AAL2',
        occurredAt: '2026-09-20T12:00:00.000Z',
      })
    ).resolves.toBe(true);

    const [, init] = request.mock.calls[0] as [string, RequestInit];
    const body = String(init.body);
    expect(request.mock.calls[0][0]).toBe('https://business.example/internal/identity/security-events');
    expect(init.headers).toMatchObject({
      'X-WAOOAW-Identity-Event-Signature': `sha256=${createHmac('sha256', signingKey).update(body).digest('hex')}`,
    });
    expect(body).not.toMatch(/token|email|subject|tenant|session/i);
  });

  it('fails closed when signing material is unavailable', async () => {
    Reflect.deleteProperty(process.env, 'IDENTITY_EVENT_SIGNING_KEY');
    await expect(
      persistWebIdentitySecurityEvent({
        correlationId: crypto.randomUUID(),
        eventType: 'CALLBACK_FAILURE',
        providerClass: 'UNKNOWN',
        outcome: 'FAILED',
        reasonCode: 'BROKER_CALLBACK_FAILED',
      })
    ).rejects.toThrow('Identity event signing is unavailable.');
  });
});
