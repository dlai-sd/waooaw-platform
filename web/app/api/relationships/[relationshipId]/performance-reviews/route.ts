import { readServerResponse } from '@/lib/server-failure';
import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

interface PerformanceReviewEnvelope {
  payload?: { commandKind?: string };
}

async function POSTHandler(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  const body = (await readRequestJson(request)) as {
    idempotencyKey?: string;
    command?: PerformanceReviewEnvelope;
  };
  if (!body.idempotencyKey || body.command?.payload?.commandKind !== 'RESPOND_TO_PERFORMANCE_REVIEW') {
    return NextResponse.json({ title: 'Performance review decision is invalid.' }, { status: 400 });
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
    'web.relationships.relationshipid.performance.reviews.response_invalid',
    { title: 'Performance review decision could not be recorded.' }
  );
  return NextResponse.json(payload, {
    status: response.status,
    headers: { 'Cache-Control': 'no-store' },
  });
}

export const POST = withServerFailureBoundary(
  'web.relationships.relationshipid.performance.reviews.post_failed',
  POSTHandler
);
