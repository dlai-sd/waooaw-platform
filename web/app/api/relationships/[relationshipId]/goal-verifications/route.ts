import { readServerResponse } from '@/lib/server-failure';
import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

interface GoalVerificationEnvelope {
  payload?: { commandKind?: string };
}

async function POSTHandler(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  const body = (await readRequestJson(request)) as {
    idempotencyKey?: string;
    command?: GoalVerificationEnvelope;
  };
  if (!body.idempotencyKey || body.command?.payload?.commandKind !== 'VERIFY_GOAL') {
    return NextResponse.json({ title: 'Goal verification is invalid.' }, { status: 400 });
  }
  const response = await fetch(
    `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/workspace/commands`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        'Idempotency-Key': body.idempotencyKey,
      },
      body: JSON.stringify(body.command),
      cache: 'no-store',
    }
  );
  const payload = await readServerResponse(
    response,
    'web.relationships.relationshipid.goal.verifications.response_invalid',
    { title: 'Goal verification could not be recorded.' }
  );
  return NextResponse.json(payload, {
    status: response.status,
    headers: { 'Cache-Control': 'no-store' },
  });
}

export const POST = withServerFailureBoundary(
  'web.relationships.relationshipid.goal.verifications.post_failed',
  POSTHandler
);
