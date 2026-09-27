import { type NextRequest, NextResponse } from 'next/server';
import { getIdentitySession } from '@/lib/api/identity';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { accessTokenFromRequest } from '@/lib/server-auth';

const versionPattern = /^\d+\.\d+\.\d+$/;

export async function POST(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const identity = await getIdentitySession(accessToken);
  if (identity.kind !== 'ready') {
    return NextResponse.json({ title: 'Complete registration before hiring a professional.' }, { status: 409 });
  }

  const body = (await request.json()) as { professionalType?: string; professionalVersion?: string };
  if (
    !body.professionalType ||
    !/^[A-Z][A-Z0-9_]{0,63}$/.test(body.professionalType) ||
    !body.professionalVersion ||
    !versionPattern.test(body.professionalVersion)
  ) {
    return NextResponse.json({ title: 'Hire commercial preview is invalid.' }, { status: 400 });
  }

  try {
    const disclosure = await getProfessionalDisclosure(body.professionalType);
    if (
      !disclosure.eligibility.eligible ||
      disclosure.projectionVersion !== body.professionalVersion ||
      disclosure.indicativePrice.currency !== 'INR'
    ) {
      return NextResponse.json({ title: 'Professional commercial terms are unavailable.' }, { status: 409 });
    }
    const response = await fetch(`${process.env.BILLING_ENGINE_URL ?? 'http://localhost:8140'}/payments/hire-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        professional_type: disclosure.professionalType,
        gross_amount_inr_paise: disclosure.indicativePrice.amountInrPaise,
        gst_amount_inr_paise: Math.floor(disclosure.indicativePrice.amountInrPaise * 18 / 118),
        cadence: disclosure.indicativePrice.cadence,
      }),
      cache: 'no-store',
    });
    const result = await response.json().catch(() => ({ title: 'Hire commercial preview is unavailable.' }));
    return NextResponse.json(result, {
      status: response.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch {
    return NextResponse.json({ title: 'Hire commercial preview is unavailable.' }, { status: 503 });
  }
}