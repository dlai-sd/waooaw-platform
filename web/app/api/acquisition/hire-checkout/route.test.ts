/** @jest-environment node */

import { NextRequest } from 'next/server';
import { getIdentitySession } from '@/lib/api/identity';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { accessTokenFromRequest } from '@/lib/server-auth';

const continueAcquisition = jest.fn();
jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/api/professionals', () => ({ getProfessionalDisclosure: jest.fn() }));
jest.mock('@/lib/api/generated/apis/ProfessionalsApi', () => ({
  ProfessionalsApi: jest.fn(() => ({ continueAcquisition })),
}));

const originalFetch = global.fetch;
const customerId = '22222222-2222-4222-8222-222222222222';
const relationshipId = '33333333-3333-4333-8333-333333333333';
const baseBody = {
  action: 'start',
  professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
  professionalVersion: '1.0.0',
  disclosureRevision: '1.0.0',
  termsVersion: '2026-07-18',
  idempotencyKey: '11111111-1111-4111-8111-111111111111',
  couponCode: 'demo100',
};

const request = (body: object) => new NextRequest('http://localhost/api/acquisition/hire-checkout', {
  method: 'POST',
  body: JSON.stringify(body),
});

describe('pre-hire checkout boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
    jest.mocked(getIdentitySession).mockResolvedValue({
      kind: 'ready',
      session: { accountReference: customerId } as never,
    });
    jest.mocked(getProfessionalDisclosure).mockResolvedValue({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      projectionVersion: '1.0.0',
      displayName: 'Digital Marketing Professional',
      suitability: [],
      eligibility: { eligible: true, explanation: 'Available' },
      customerRouteSlug: 'digital-marketing-local-service',
      disclosureRevision: '1.0.0',
      termsVersion: '2026-07-18',
      skills: [],
      limitations: [],
      authorityNeeds: [],
      customerRights: [],
      trial: { available: true, durationDays: 14, paidApiCallsAllowed: false, externalActionsAllowed: false },
      evidencePosture: 'Evidence First',
      indicativePrice: { currency: 'INR', amountInrPaise: 118000, cadence: 'MONTHLY', qualification: 'Indicative' },
    });
    continueAcquisition.mockResolvedValue({ relationshipId, resumePath: `/relationships/${relationshipId}` });
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('creates a Razorpay order from canonical server pricing without creating a relationship', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcome_kind: 'RAZORPAY_CHECKOUT_REQUIRED',
        checkout_intent_id: baseBody.idempotencyKey,
        provider_order_reference: 'order_test123',
        amount_inr_paise: 118000,
        currency: 'INR',
      }),
    });
    const { POST } = await import('./route');

    const response = await POST(request({ ...baseBody, grossAmountInrPaise: 1 }));

    expect(response.status).toBe(200);
    expect(continueAcquisition).not.toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8140/payments/hire-checkout',
      expect.objectContaining({ method: 'POST' })
    );
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[0][1]?.body))).toEqual(
      expect.objectContaining({
        customer_id: customerId,
        gross_amount_inr_paise: 118000,
        gst_amount_inr_paise: 18000,
        coupon_code: 'DEMO100',
      })
    );
  });

  it('creates and binds the relationship only after signed confirmation is captured', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          outcome_kind: 'CAPTURED',
          checkout_intent_id: baseBody.idempotencyKey,
          commercial_outcome_reference: 'pay_test123',
          commercial_evidence_id: '44444444-4444-4444-8444-444444444444',
          amount_inr_paise: 118000,
          currency: 'INR',
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ outcome_kind: 'CAPTURED' }) });
    const { POST } = await import('./route');

    const response = await POST(request({
      ...baseBody,
      action: 'confirm',
      razorpayOrderId: 'order_test123',
      razorpayPaymentId: 'pay_test123',
      razorpaySignature: 'a'.repeat(64),
    }));

    expect(response.status).toBe(200);
    expect(continueAcquisition).toHaveBeenCalledTimes(1);
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      `http://localhost:8140/payments/hire-checkout/${baseBody.idempotencyKey}/bind`,
      expect.objectContaining({ body: JSON.stringify({ customer_id: customerId, relationship_id: relationshipId }) })
    );
    expect(await response.json()).toEqual(expect.objectContaining({ resumePath: `/relationships/${relationshipId}` }));
  });
});