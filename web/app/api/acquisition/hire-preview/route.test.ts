/** @jest-environment node */

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
// Constitutional basis: C-023, C-059, C-063

import { NextRequest } from 'next/server';
import { getIdentitySession } from '@/lib/api/identity';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { accessTokenFromRequest } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/api/professionals', () => ({ getProfessionalDisclosure: jest.fn() }));

const originalFetch = global.fetch;
const quoteResponse = (overrides: Record<string, unknown> = {}) =>
  ({
    ok: true,
    status: 200,
    json: async () => ({
      packageCode: 'STARTER',
      currency: 'INR',
      grossAmountInrPaise: 118000,
      gstAmountInrPaise: 18000,
      basePriceInrPaise: 100000,
      cadence: 'MONTHLY',
      billingPeriodDays: 30,
      quoteVersion: 'c'.repeat(64),
      ...overrides,
    }),
  }) as Response;
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

  it('prices the preview from the server-resolved quote and forwards normalized coupon input for Billing validation', async () => {
    jest.mocked(getProfessionalDisclosure).mockResolvedValue(disclosure());
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce(quoteResponse())
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({ coupon_code: 'DEMO100', payable_inr_paise: 0 }),
      } as Response)
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ items: [] }) } as Response);
    const { POST } = await import('./route');

    const response = await POST(request());

    expect(response.status).toBe(200);
    const [quoteUrl, quoteInit] = jest.mocked(global.fetch).mock.calls[0];
    expect(quoteUrl).toBe('http://localhost:5001/api/v1/acquisition/hire-quote');
    expect((quoteInit as RequestInit).headers).toMatchObject({ Authorization: 'Bearer access-token' });
    // The client's grossAmountInrPaise is never forwarded to the quote owner.
    expect(JSON.parse(String((quoteInit as RequestInit).body))).toEqual({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      professionalVersion: '1.0.0',
    });
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8140/payments/hire-preview',
      expect.objectContaining({
        body: JSON.stringify({
          professional_type: 'DIGITAL_MARKETING_LOCAL_SERVICE',
          professional_version: '1.0.0',
          gross_amount_inr_paise: 118000,
          gst_amount_inr_paise: 18000,
          cadence: 'MONTHLY',
          coupon_code: 'ATTACKER100',
        }),
      })
    );
    expect(await response.json()).toMatchObject({
      coupon_code: 'DEMO100',
      payable_inr_paise: 0,
      quoteVersion: 'c'.repeat(64),
      package: { packageCode: 'STARTER', priceInclGstPaise: 118000 },
    });
  });

  it('has no preview and calls Billing for nothing when no package is for sale', async () => {
    jest.mocked(getProfessionalDisclosure).mockResolvedValue(disclosure());
    global.fetch = jest.fn().mockResolvedValueOnce({ ok: false, status: 409, json: async () => ({}) } as Response);
    const { POST } = await import('./route');

    const response = await POST(request());

    expect(response.status).toBe(409);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['an owner outage', () => Promise.resolve({ ok: false, status: 503, json: async () => ({}) } as Response)],
    ['a network failure', () => Promise.reject(new Error('connect ECONNREFUSED'))],
    ['a malformed quote', () => Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)],
  ])('is unavailable on %s and never falls back to another price', async (_name, answer) => {
    jest.mocked(getProfessionalDisclosure).mockResolvedValue(disclosure());
    global.fetch = jest.fn().mockImplementationOnce(answer);
    const { POST } = await import('./route');

    const response = await POST(request());

    expect(response.status).toBe(503);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  const disclosure = () =>
    ({
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
    }) as never;
  const catalogue = {
    items: [
      {
        packageCode: 'GROWTH',
        displayName: 'Growth',
        billingPeriodDays: 30,
        priceInclGstPaise: 236000,
        basePricePaise: 200000,
        gstPaise: 36000,
        components: [
          { componentId: 'PROACTIVE_MESSAGE', label: 'Proactive messages', quantity: 30, cadence: 'SPREAD' },
        ],
      },
    ],
  };

  it('prices an explicit package from the quote and returns its components from the catalogue', async () => {
    jest.mocked(getProfessionalDisclosure).mockResolvedValue(disclosure());
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce(
        quoteResponse({
          packageCode: 'GROWTH',
          grossAmountInrPaise: 236000,
          gstAmountInrPaise: 36000,
          basePriceInrPaise: 200000,
        })
      )
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({ payable_inr_paise: 236000 }) } as Response)
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => catalogue } as Response);
    const { POST } = await import('./route');

    const response = await POST(
      new NextRequest('http://localhost/api/acquisition/hire-preview', {
        method: 'POST',
        body: JSON.stringify({
          professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
          professionalVersion: '1.0.0',
          packageCode: 'GROWTH',
        }),
      })
    );

    expect(JSON.parse(String((jest.mocked(global.fetch).mock.calls[0][1] as RequestInit).body))).toMatchObject({
      packageCode: 'GROWTH',
    });
    expect(jest.mocked(global.fetch).mock.calls[1][1]).toMatchObject({
      body: JSON.stringify({
        professional_type: 'DIGITAL_MARKETING_LOCAL_SERVICE',
        professional_version: '1.0.0',
        gross_amount_inr_paise: 236000,
        gst_amount_inr_paise: 36000,
        cadence: 'MONTHLY',
      }),
    });
    const [packageUrl, packageInit] = jest.mocked(global.fetch).mock.calls[2];
    expect(packageUrl).toBe(
      'http://localhost:5001/api/v1/marketplace/agents/DIGITAL_MARKETING_LOCAL_SERVICE/versions/1.0.0/packages?limit=100'
    );
    expect((packageInit as RequestInit).headers).toMatchObject({ Authorization: 'Bearer access-token' });
    const result = await response.json();
    expect(result.package).toMatchObject({ packageCode: 'GROWTH', billingPeriodDays: 30 });
    expect(result.package.components).toHaveLength(1);
  });

  it('refuses a package code that the server does not offer', async () => {
    jest.mocked(getProfessionalDisclosure).mockResolvedValue(disclosure());
    global.fetch = jest.fn().mockResolvedValueOnce({ ok: false, status: 409, json: async () => ({}) } as Response);
    const { POST } = await import('./route');

    const response = await POST(
      new NextRequest('http://localhost/api/acquisition/hire-preview', {
        method: 'POST',
        body: JSON.stringify({
          professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
          professionalVersion: '1.0.0',
          packageCode: 'UNLISTED',
        }),
      })
    );

    expect(response.status).toBe(409);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });
});
