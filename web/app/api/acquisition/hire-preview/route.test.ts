/** @jest-environment node */

import { NextRequest } from 'next/server';
import { getIdentitySession } from '@/lib/api/identity';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/api/professionals', () => ({ getProfessionalDisclosure: jest.fn() }));

const originalFetch = global.fetch;
const request = () =>
  new NextRequest('http://localhost/api/acquisition/hire-preview', {
    method: 'POST',
    body: JSON.stringify({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      professionalVersion: '1.0.0',
      grossAmountInrPaise: 1,
      couponCode: 'ATTACKER100',
    }),
  });

describe('Hire commercial preview boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(accessTokenFromRequest).mockResolvedValue('access-token');
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'ready', session: {} as never });
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('rejects preview before customer registration', async () => {
    jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'registration-required' });
    const { POST } = await import('./route');

    expect((await POST(request())).status).toBe(409);
    expect(getProfessionalDisclosure).not.toHaveBeenCalled();
  });

  it('uses server disclosure price and forwards normalized coupon input for Billing validation', async () => {
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
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      json: async () => ({ coupon_code: 'DEMO100', payable_inr_paise: 0 }),
    } as Response);
    const { POST } = await import('./route');

    const response = await POST(request());

    expect(response.status).toBe(200);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8140/payments/hire-preview',
      expect.objectContaining({
        body: JSON.stringify({
          professional_type: 'DIGITAL_MARKETING_LOCAL_SERVICE',
          gross_amount_inr_paise: 118000,
          gst_amount_inr_paise: 18000,
          cadence: 'MONTHLY',
          coupon_code: 'ATTACKER100',
        }),
      })
    );
    expect(await response.json()).toEqual({ coupon_code: 'DEMO100', payable_inr_paise: 0 });
  });
});