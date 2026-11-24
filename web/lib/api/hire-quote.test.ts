/** @jest-environment node */

// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R013
// Constitutional basis: C-023, C-059, C-063

import { resolveHireQuote } from './hire-quote';

const originalFetch = global.fetch;
const quote = {
  packageCode: 'STARTER',
  currency: 'INR',
  grossAmountInrPaise: 118000,
  gstAmountInrPaise: 18000,
  basePriceInrPaise: 100000,
  cadence: 'MONTHLY',
  billingPeriodDays: 30,
  quoteVersion: 'a'.repeat(64),
};

describe('resolveHireQuote', () => {
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('returns the Business Platform quote for the signed-in customer and sends no amount', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200, json: async () => quote });

    const result = await resolveHireQuote('access-token', 'DMA', '1.0.0', 'STARTER');

    expect(result).toEqual({ kind: 'quote', quote });
    const [url, init] = jest.mocked(global.fetch).mock.calls[0];
    expect(url).toBe('http://localhost:5001/api/v1/acquisition/hire-quote');
    expect((init as RequestInit).headers).toMatchObject({ Authorization: 'Bearer access-token' });
    expect(JSON.parse(String((init as RequestInit).body))).toEqual({
      professionalType: 'DMA',
      professionalVersion: '1.0.0',
      packageCode: 'STARTER',
    });
  });

  it.each([
    ['no package is for sale', { ok: false, status: 409, json: async () => ({}) }, 'not-offered'],
    ['the owner is unavailable', { ok: false, status: 503, json: async () => ({}) }, 'unavailable'],
    ['the customer has no workspace', { ok: false, status: 403, json: async () => ({}) }, 'unavailable'],
    [
      'the quote is zero',
      { ok: true, status: 200, json: async () => ({ ...quote, grossAmountInrPaise: 0 }) },
      'unavailable',
    ],
    [
      'the quote is not INR',
      { ok: true, status: 200, json: async () => ({ ...quote, currency: 'USD' }) },
      'unavailable',
    ],
    [
      'the version is malformed',
      { ok: true, status: 200, json: async () => ({ ...quote, quoteVersion: 'x' }) },
      'unavailable',
    ],
  ])('is %s: %s', async (_name, answer, kind) => {
    global.fetch = jest.fn().mockResolvedValue(answer);

    expect((await resolveHireQuote('access-token', 'DMA', '1.0.0')).kind).toBe(kind);
  });

  it('is unavailable, not a fallback amount, when the network fails', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('connect ECONNREFUSED'));

    expect(await resolveHireQuote('access-token', 'DMA', '1.0.0')).toEqual({ kind: 'unavailable' });
  });
});
