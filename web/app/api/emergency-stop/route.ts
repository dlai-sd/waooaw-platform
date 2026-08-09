import { NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

export async function POST(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ error: 'UNAUTHENTICATED' }, { status: 401 });

  const body = (await request.json()) as { contractId?: string; activeSessionIds?: string[] };
  if (!body.contractId) {
    return NextResponse.json({ error: 'NO_ACTIVE_STOP_TARGET' }, { status: 409 });
  }

  const runtimeUrl = process.env.PROFESSIONAL_RUNTIME_URL ?? 'http://localhost:5003';
  const response = await fetch(`${runtimeUrl}/api/v1/emergency-stop`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    cache: 'no-store',
  });
  const payload = await response.json().catch(() => ({ error: 'STOP_RESPONSE_UNREADABLE' }));
  return NextResponse.json(payload, { status: response.status });
}