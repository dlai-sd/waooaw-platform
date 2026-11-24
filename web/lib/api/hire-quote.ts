// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R013
// Constitutional basis: C-023, C-059, C-063

import { logServerFailure } from '@/lib/server-failure';

export interface HireQuote {
  packageCode: string;
  currency: string;
  grossAmountInrPaise: number;
  gstAmountInrPaise: number;
  basePriceInrPaise: number;
  cadence: string;
  billingPeriodDays: number;
  quoteVersion: string;
}

export type HireQuoteResult = { kind: 'quote'; quote: HireQuote } | { kind: 'not-offered' } | { kind: 'unavailable' };

const quoteVersionPattern = /^[0-9a-f]{64}$/;

export function isHireQuote(value: unknown): value is HireQuote {
  if (!value || typeof value !== 'object') return false;
  const quote = value as Record<string, unknown>;
  return (
    typeof quote.packageCode === 'string' &&
    quote.currency === 'INR' &&
    Number.isSafeInteger(quote.grossAmountInrPaise) &&
    (quote.grossAmountInrPaise as number) > 0 &&
    Number.isSafeInteger(quote.gstAmountInrPaise) &&
    (quote.gstAmountInrPaise as number) >= 0 &&
    Number.isSafeInteger(quote.basePriceInrPaise) &&
    typeof quote.cadence === 'string' &&
    Number.isSafeInteger(quote.billingPeriodDays) &&
    typeof quote.quoteVersion === 'string' &&
    quoteVersionPattern.test(quote.quoteVersion)
  );
}

/**
 * The only price a customer's Hire is shown or charged at. The Business Platform resolves it from the billing owner's
 * for-sale monthly packages; any failure means there is no amount, never a fallback.
 */
export async function resolveHireQuote(
  accessToken: string,
  professionalType: string,
  professionalVersion: string,
  packageCode?: string
): Promise<HireQuoteResult> {
  try {
    const response = await fetch(
      `${process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001'}/api/v1/acquisition/hire-quote`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({ professionalType, professionalVersion, ...(packageCode ? { packageCode } : {}) }),
        cache: 'no-store',
      }
    );
    if (response.status === 409) return { kind: 'not-offered' };
    if (!response.ok) return { kind: 'unavailable' };
    const quote = await response.json();
    return isHireQuote(quote) ? { kind: 'quote', quote } : { kind: 'unavailable' };
  } catch (error) {
    logServerFailure('web.acquisition.hire.quote.unavailable', error);
    return { kind: 'unavailable' };
  }
}
