import { NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const scopeConfirmation = 'I_CONFIRM_THE_ACCEPTED_DECISION_SPACE_AND_AUTHORITY_SCOPE';

export async function POST(request: NextRequest, { params }: { params: { relationshipId: string } }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const body = await request.json();
  const root = `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(params.relationshipId)}/contracts/${body.version}`;
  const target = body.action === 'accept' ? `${root}/accept` : body.action === 'pay' ? `${root}/payments/onboarding-order` : null;
  if (!target) return NextResponse.json({ title: 'Contract request is invalid.' }, { status: 400 });
  if (typeof body.idempotencyKey !== 'string' || body.idempotencyKey.length === 0) return NextResponse.json({ title: 'Contract request is invalid.' }, { status: 400 });
  const payload = body.action === 'accept'
    ? { contractHash: body.contractHash, scopeConfirmation }
    : { bundleTier: 'CONTRACT', subscriptionAmountInrPaise: body.grossAmountInrPaise, walletSeedInrPaise: 0, proceedConfirmation: 'PROCEED_TO_RAZORPAY' };
  const response = await fetch(target, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json', 'Idempotency-Key': body.idempotencyKey }, body: JSON.stringify(payload), cache: 'no-store' });
  const result = await response.json();
  return NextResponse.json(result, { status: response.status, headers: { 'Cache-Control': 'no-store' } });
}