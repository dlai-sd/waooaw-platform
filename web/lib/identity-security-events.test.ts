/** @jest-environment node */

import { createHmac } from 'node:crypto';
import { persistWebIdentitySecurityEvent, recordWebIdentitySecurityEvent } from './identity-security-events';

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

  it('bounds Business Platform persistence requests to five seconds', async () => {
    const signal = new AbortController().signal;
    const timeout = jest.spyOn(AbortSignal, 'timeout').mockReturnValue(signal);
    const request = jest.fn().mockResolvedValue(new Response(null, { status: 201 }));
    Object.defineProperty(globalThis, 'fetch', { configurable: true, value: request });

    await persistWebIdentitySecurityEvent({
      correlationId: crypto.randomUUID(),
      eventType: 'SESSION_EXPIRY',
      providerClass: 'GOOGLE',
      outcome: 'SUCCEEDED',
      reasonCode: 'SESSION_EXPIRED',
    });

    expect(timeout).toHaveBeenCalledWith(5_000);
    expect(request.mock.calls[0][1]).toMatchObject({ signal });
  });

  it('reports an accepted duplicate without claiming a new durable insert', async () => {
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: jest.fn().mockResolvedValue(new Response(null, { status: 200 })),
    });

    await expect(
      persistWebIdentitySecurityEvent({
        correlationId: crypto.randomUUID(),
        sourceEventId: 'web:duplicate-event',
        eventType: 'CALLBACK_SUCCESS',
        providerClass: 'GOOGLE',
        outcome: 'SUCCEEDED',
        reasonCode: 'BROKER_CALLBACK_VALID',
      })
    ).resolves.toBe(false);
  });

  it('rejects a dependency response without reporting durable success', async () => {
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: jest.fn().mockResolvedValue(new Response(null, { status: 503 })),
    });

    await expect(
      persistWebIdentitySecurityEvent({
        correlationId: crypto.randomUUID(),
        eventType: 'CALLBACK_FAILURE',
        providerClass: 'UNKNOWN',
        outcome: 'FAILED',
        reasonCode: 'BROKER_CALLBACK_FAILED',
      })
    ).rejects.toThrow('Identity event persistence failed with status 503.');
  });

  it('reports transport timeout without rejecting the customer flow', async () => {
    const timeout = new DOMException('The operation timed out.', 'TimeoutError');
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: jest.fn().mockRejectedValue(timeout),
    });
    const error = jest.spyOn(console, 'error').mockImplementation(() => undefined);

    await expect(
      recordWebIdentitySecurityEvent({
        correlationId: crypto.randomUUID(),
        eventType: 'PROVIDER_HANDOFF',
        providerClass: 'GOOGLE',
        outcome: 'ATTEMPTED',
        reasonCode: 'BROKER_REDIRECT_REQUESTED',
      })
    ).resolves.toBeUndefined();
    expect(error).toHaveBeenCalledWith('Identity security event was not persisted.', {
      eventType: 'PROVIDER_HANDOFF',
      reason: 'TimeoutError',
    });
  });
});
