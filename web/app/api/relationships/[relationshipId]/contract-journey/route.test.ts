/** @jest-environment node */

import { NextRequest } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));

const originalFetch = global.fetch;
const params = Promise.resolve({ relationshipId: '33333333-3333-4333-8333-333333333333' });

const confirmationRequest = (signature = 'a'.repeat(64)) =>
  new NextRequest('http://localhost/api/relationships/33333333-3333-4333-8333-333333333333/contract-journey', {
    method: 'POST',
    body: JSON.stringify({
      action: 'confirm',
      checkoutIntentId: '22222222-2222-4222-8222-222222222222',
      razorpayOrderId: 'order_test_123',
      razorpayPaymentId: 'pay_test_123',
      razorpaySignature: signature,
    }),
  });

describe('relationship Razorpay confirmation boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('sends signed provider fields to Billing and reconciles through the customer-authorized relationship API', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ outcome_kind: 'CAPTURED' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ outcomeKind: 'CAPTURED' }),
      });
    const { POST } = await import('./route');

    const response = await POST(confirmationRequest(), { params });

    expect(response.status).toBe(200);
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      'http://localhost:8140/payments/relationship-checkout/22222222-2222-4222-8222-222222222222/confirm',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          razorpay_order_id: 'order_test_123',
          razorpay_payment_id: 'pay_test_123',
          razorpay_signature: 'a'.repeat(64),
        }),
      })
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      'http://localhost:5001/api/v1/employment/relationships/33333333-3333-4333-8333-333333333333/checkout-intents/22222222-2222-4222-8222-222222222222',
      expect.objectContaining({ headers: { Authorization: 'Bearer access-token' } })
    );
  });

  it('rejects malformed provider signatures before contacting Billing', async () => {
    global.fetch = jest.fn();
    const { POST } = await import('./route');

    const response = await POST(confirmationRequest('not-a-signature'), { params });

    expect(response.status).toBe(400);
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
