import { type NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ relationshipId: string }> }
) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const idempotencyKey = request.headers.get('Idempotency-Key');
  if (!idempotencyKey) return NextResponse.json({ title: 'Hire setup request is invalid.' }, { status: 400 });
  const { relationshipId } = await params;
  const body = await request.json();
  const response = await fetch(
    `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/hire-setup`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey,
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    }
  );
  const result = await response.json().catch(() => ({ title: 'Hire setup remains unresolved.' }));
  return NextResponse.json(result, {
    status: response.status,
    headers: { 'Cache-Control': 'no-store' },
  });
}