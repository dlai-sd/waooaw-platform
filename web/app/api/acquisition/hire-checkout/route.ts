import { persistAcquisitionIntent } from '@/lib/api/acquisition-intent';
import { ProfessionalsApi } from '@/lib/api/generated/apis/ProfessionalsApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { getIdentitySession } from '@/lib/api/identity';
import { createMyAgentsSelection, myAgentsSelectionCookie } from '@/lib/api/my-agents-selection';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { withJourneyTrace } from '@/lib/journey-telemetry';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { type NextRequest, NextResponse } from 'next/server';

const billingEngineUrl = process.env.BILLING_ENGINE_URL ?? 'http://localhost:8140';
const versionPattern = /^\d+\.\d+\.\d+$/;
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const orderPattern = /^order_[A-Za-z0-9_-]{1,120}$/;
const paymentPattern = /^pay_[A-Za-z0-9_-]{1,122}$/;

interface HireCheckoutCommand {
  action?: 'start' | 'confirm' | 'cancel';
  professionalType?: string;
  professionalVersion?: string;
  disclosureRevision?: string;
  termsVersion?: string;
  idempotencyKey?: string;
  contractAcceptance?: string;
  couponCode?: string;
  razorpayOrderId?: string;
  razorpayPaymentId?: string;
  razorpaySignature?: string;
}

interface BillingCheckoutOutcome {
  outcome_kind: string;
  checkout_intent_id: string;
  provider_order_reference?: string;
  public_checkout_key?: string;
  amount_inr_paise: number;
  currency: string;
  merchant_display_name?: string;
  enabled_method_families?: string[];
  expires_at?: string;
  commercial_outcome_reference?: string;
  commercial_evidence_id?: string;
  customer_safe_next_action?: string;
}

async function hireCheckout(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });

  const body = (await request.json()) as HireCheckoutCommand;
  if (
    (body.action !== 'start' && body.action !== 'confirm' && body.action !== 'cancel') ||
    !body.professionalType ||
    !/^[A-Z][A-Z0-9_]{0,63}$/.test(body.professionalType) ||
    !body.professionalVersion ||
    !versionPattern.test(body.professionalVersion) ||
    !body.disclosureRevision ||
    !versionPattern.test(body.disclosureRevision) ||
    !body.termsVersion ||
    !/^\d{4}-\d{2}-\d{2}$/.test(body.termsVersion) ||
    !body.idempotencyKey ||
    !uuidPattern.test(body.idempotencyKey) ||
    body.contractAcceptance !== 'ACCEPT_EMPLOYMENT_CONTRACT'
  ) {
    return NextResponse.json({ title: 'Hire checkout request is invalid.' }, { status: 400 });
  }

  const persisted = await persistAcquisitionIntent(accessToken, body.idempotencyKey, {
    professionalType: body.professionalType,
    professionalVersion: body.professionalVersion,
    intent: 'HIRE',
    disclosureRevision: body.disclosureRevision,
    termsVersion: body.termsVersion,
    acceptance: body.contractAcceptance,
    ...(body.couponCode ? { couponCode: body.couponCode.trim().toUpperCase() } : {}),
  });
  if (!persisted.ok) {
    const payload = await persisted.json().catch(() => ({ title: 'Acquisition intent could not be saved.' }));
    return NextResponse.json(payload, { status: persisted.status, headers: { 'Cache-Control': 'no-store' } });
  }

  const identity = await getIdentitySession(accessToken);
  if (identity.kind !== 'ready') {
    return NextResponse.json(
      {
        code: identity.kind === 'registration-required' ? 'REGISTRATION_REQUIRED' : undefined,
        title:
          identity.kind === 'registration-required'
            ? 'Complete registration before hiring.'
            : 'Hiring is not permitted.',
      },
      { status: identity.kind === 'registration-required' ? 409 : 403 }
    );
  }
  if (!uuidPattern.test(identity.session.accountReference)) {
    return NextResponse.json({ title: 'Hire checkout request is invalid.' }, { status: 400 });
  }

  try {
    const correlationId = body.idempotencyKey;
    const disclosure = await getProfessionalDisclosure(body.professionalType);
    if (
      !disclosure.eligibility.eligible ||
      disclosure.projectionVersion !== body.professionalVersion ||
      disclosure.disclosureRevision !== body.disclosureRevision ||
      disclosure.termsVersion !== body.termsVersion ||
      disclosure.indicativePrice.currency !== 'INR'
    ) {
      return NextResponse.json(
        { title: 'Professional commercial terms have changed. Review the offer again.' },
        { status: 409 }
      );
    }

    let outcome: BillingCheckoutOutcome;
    if (body.action === 'start') {
      const billingResponse = await fetch(`${billingEngineUrl}/payments/hire-checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Correlation-ID': correlationId },
        body: JSON.stringify({
          checkout_intent_id: body.idempotencyKey,
          correlation_id: correlationId,
          customer_id: identity.session.accountReference,
          professional_type: disclosure.professionalType,
          professional_version: disclosure.projectionVersion,
          disclosure_revision: disclosure.disclosureRevision,
          terms_version: disclosure.termsVersion,
          gross_amount_inr_paise: disclosure.indicativePrice.amountInrPaise,
          gst_amount_inr_paise: Math.floor((disclosure.indicativePrice.amountInrPaise * 18) / 118),
          cadence: disclosure.indicativePrice.cadence,
          ...(typeof body.couponCode === 'string' && body.couponCode.trim()
            ? { coupon_code: body.couponCode.trim().toUpperCase() }
            : {}),
        }),
        cache: 'no-store',
      });
      const result = await billingResponse.json().catch(() => ({ title: 'Secure checkout is unavailable.' }));
      if (!billingResponse.ok) {
        return NextResponse.json(result, { status: billingResponse.status, headers: { 'Cache-Control': 'no-store' } });
      }
      outcome = result as BillingCheckoutOutcome;
    } else if (body.action === 'confirm') {
      if (
        !body.razorpayOrderId ||
        !orderPattern.test(body.razorpayOrderId) ||
        !body.razorpayPaymentId ||
        !paymentPattern.test(body.razorpayPaymentId) ||
        !body.razorpaySignature ||
        !/^[0-9a-f]{64}$/i.test(body.razorpaySignature)
      ) {
        return NextResponse.json({ title: 'Razorpay payment confirmation is invalid.' }, { status: 400 });
      }
      const billingResponse = await fetch(`${billingEngineUrl}/payments/hire-checkout/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          checkout_intent_id: body.idempotencyKey,
          customer_id: identity.session.accountReference,
          razorpay_order_id: body.razorpayOrderId,
          razorpay_payment_id: body.razorpayPaymentId,
          razorpay_signature: body.razorpaySignature,
        }),
        cache: 'no-store',
      });
      const result = await billingResponse.json().catch(() => ({ title: 'Payment confirmation is unavailable.' }));
      if (!billingResponse.ok) {
        return NextResponse.json(result, { status: billingResponse.status, headers: { 'Cache-Control': 'no-store' } });
      }
      outcome = result as BillingCheckoutOutcome;
    } else {
      const billingResponse = await fetch(`${billingEngineUrl}/payments/hire-checkout/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          checkout_intent_id: body.idempotencyKey,
          customer_id: identity.session.accountReference,
        }),
        cache: 'no-store',
      });
      const result = await billingResponse.json().catch(() => ({ title: 'Checkout cancellation is unavailable.' }));
      return NextResponse.json(result, {
        status: billingResponse.status,
        headers: { 'Cache-Control': 'no-store' },
      });
    }

    if (outcome.outcome_kind !== 'CAPTURED' && outcome.outcome_kind !== 'FULLY_DISCOUNTED') {
      return NextResponse.json(outcome, { headers: { 'Cache-Control': 'no-store' } });
    }

    const api = new ProfessionalsApi(
      new Configuration({ basePath: process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001', accessToken })
    );
    const continuation = await api.continueAcquisition(
      {
        idempotencyKey: body.idempotencyKey,
        xCorrelationID: correlationId,
        continueAcquisitionRequest: {
          professionalType: body.professionalType,
          professionalVersion: body.professionalVersion,
          intent: 'HIRE',
          disclosureRevision: body.disclosureRevision,
          termsVersion: new Date(`${body.termsVersion}T00:00:00.000Z`),
          acceptance: body.contractAcceptance,
          ...(body.couponCode ? { couponCode: body.couponCode.trim().toUpperCase() } : {}),
        },
      },
      { cache: 'no-store' }
    );
    const bindResponse = await fetch(`${billingEngineUrl}/payments/hire-checkout/bind`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        checkout_intent_id: body.idempotencyKey,
        customer_id: identity.session.accountReference,
        relationship_id: continuation.relationshipId,
      }),
      cache: 'no-store',
    });
    if (!bindResponse.ok) {
      return NextResponse.json(
        { title: 'Payment was received, but Hire setup is still being reconciled. Retry the same request.' },
        { status: 503, headers: { 'Cache-Control': 'no-store' } }
      );
    }
    const selection = await createMyAgentsSelection(
      accessToken,
      continuation.relationshipId,
      outcome.outcome_kind === 'CAPTURED' ? 'HIRE_PAID' : 'HIRE_ZERO_PRICE'
    );
    const response = NextResponse.json(
      { ...outcome, resumePath: '/professionals/mine' },
      { headers: { 'Cache-Control': 'no-store' } }
    );
    response.cookies.set(myAgentsSelectionCookie, selection.handle, {
      expires: new Date(selection.expiresAt),
      httpOnly: true,
      path: '/professionals/mine',
      sameSite: 'strict',
      secure: true,
    });
    return response;
  } catch (error) {
    if (error instanceof ResponseError) {
      const payload = await error.response.json().catch(() => ({ title: 'Hire could not continue.' }));
      return NextResponse.json(payload, { status: error.response.status, headers: { 'Cache-Control': 'no-store' } });
    }
    return NextResponse.json(
      { title: 'Secure Hire checkout is unavailable.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

export const POST = (request: NextRequest) => withJourneyTrace('hire.checkout', () => hireCheckout(request));
