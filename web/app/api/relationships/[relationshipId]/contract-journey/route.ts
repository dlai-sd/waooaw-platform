import { type NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const scopeConfirmation = 'I_CONFIRM_THE_ACCEPTED_DECISION_SPACE_AND_AUTHORITY_SCOPE';

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
  const relationshipRoot = `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}`;
  const contractRoot = `${relationshipRoot}/contracts/${body.version}`;
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
