import { NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { EmploymentApi } from '@/lib/api/generated/apis/EmploymentApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';

export async function POST(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ error: 'UNAUTHENTICATED' }, { status: 401 });

  const body = (await request.json()) as { contractId?: string; activeSessionIds?: string[] };
  if (!body.contractId) {
    return NextResponse.json({ error: 'NO_ACTIVE_STOP_TARGET' }, { status: 409 });
  }

  const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
  const api = new EmploymentApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
  try {
    const stopped = await api.stopEmploymentRelationship({
      relationshipId: body.contractId,
      stopEmploymentRelationshipRequest: { correlationId: crypto.randomUUID() },
    });
    return NextResponse.json(stopped);
  } catch (error) {
    if (error instanceof ResponseError) {
      const payload = await error.response.json().catch(() => ({ error: 'STOP_RESPONSE_UNREADABLE' }));
      return NextResponse.json(payload, { status: error.response.status });
    }
    return NextResponse.json({ error: 'STOP_RESPONSE_UNREADABLE' }, { status: 503 });
  }
}