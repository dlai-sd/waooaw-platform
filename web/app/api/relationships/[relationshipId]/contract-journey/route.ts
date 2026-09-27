import { type NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const billingEngineUrl = process.env.BILLING_ENGINE_URL ?? 'http://localhost:8140';
const scopeConfirmation = 'I_CONFIRM_THE_ACCEPTED_DECISION_SPACE_AND_AUTHORITY_SCOPE';
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function GET(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const checkoutIntentId = request.nextUrl.searchParams.get('checkoutIntentId');
  if (!checkoutIntentId)
    return NextResponse.json({ title: 'Checkout reconciliation request is invalid.' }, { status: 400 });
  const { relationshipId } = await params;
  const response = await fetch(
    `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/checkout-intents/${encodeURIComponent(checkoutIntentId)}`,
    { headers: { Authorization: `Bearer ${accessToken}` }, cache: 'no-store' }
  );
  const result = await response.json().catch(() => ({ title: 'Checkout reconciliation remains unresolved.' }));
  return NextResponse.json(result, { status: response.status, headers: { 'Cache-Control': 'no-store' } });
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  const body = await request.json();
  if (body.action === 'confirm') {
    if (
      typeof body.checkoutIntentId !== 'string' ||
      !uuidPattern.test(body.checkoutIntentId) ||
      typeof body.razorpayOrderId !== 'string' ||
      !/^order_[A-Za-z0-9_-]{1,120}$/.test(body.razorpayOrderId) ||
      typeof body.razorpayPaymentId !== 'string' ||
      !/^pay_[A-Za-z0-9_-]{1,122}$/.test(body.razorpayPaymentId) ||
      typeof body.razorpaySignature !== 'string' ||
      !/^[0-9a-f]{64}$/i.test(body.razorpaySignature)
    ) {
      return NextResponse.json({ title: 'Razorpay payment confirmation is invalid.' }, { status: 400 });
    }
    const confirmation = await fetch(
      `${billingEngineUrl}/payments/relationship-checkout/${encodeURIComponent(body.checkoutIntentId)}/confirm`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          razorpay_order_id: body.razorpayOrderId,
          razorpay_payment_id: body.razorpayPaymentId,
          razorpay_signature: body.razorpaySignature,
        }),
        cache: 'no-store',
      }
    );
    const confirmationResult = await confirmation.json().catch(() => ({ title: 'Payment confirmation failed.' }));
    if (!confirmation.ok) {
      return NextResponse.json(confirmationResult, {
        status: confirmation.status,
        headers: { 'Cache-Control': 'no-store' },
      });
    }
    const reconciliation = await fetch(
      `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/checkout-intents/${encodeURIComponent(body.checkoutIntentId)}`,
      { headers: { Authorization: `Bearer ${accessToken}` }, cache: 'no-store' }
    );
    const result = await reconciliation.json().catch(() => ({ title: 'Payment reconciliation remains unresolved.' }));
    return NextResponse.json(result, {
      status: reconciliation.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  }
  if (body.action !== 'activate' && (!Number.isInteger(body.version) || body.version < 1))
    return NextResponse.json({ title: 'Contract request is invalid.' }, { status: 400 });
  const relationshipRoot = `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}`;
  const contractRoot = `${relationshipRoot}/contracts/${encodeURIComponent(String(body.version))}`;
  const target =
    body.action === 'accept'
      ? `${contractRoot}/accept`
      : body.action === 'pay'
        ? `${contractRoot}/payments/onboarding-order`
        : body.action === 'activate'
          ? `${relationshipRoot}/activation`
          : null;
  if (!target) return NextResponse.json({ title: 'Contract request is invalid.' }, { status: 400 });
  if (typeof body.idempotencyKey !== 'string' || body.idempotencyKey.length === 0)
    return NextResponse.json({ title: 'Contract request is invalid.' }, { status: 400 });
  const payload =
    body.action === 'accept'
      ? { contractHash: body.contractHash, scopeConfirmation }
      : body.action === 'pay'
        ? { proceedConfirmation: 'CONFIRM_CHECKOUT_AND_RENEWAL_TERMS' }
        : {
            commercialOutcomeKind: body.commercialOutcomeKind,
            commercialOutcomeReference: body.commercialOutcomeReference,
            commercialEvidenceId: body.commercialEvidenceId,
          };
  const response = await fetch(target, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': body.idempotencyKey,
    },
    body: JSON.stringify(payload),
    cache: 'no-store',
  });
  const result = await response.json();
  return NextResponse.json(result, { status: response.status, headers: { 'Cache-Control': 'no-store' } });
}
