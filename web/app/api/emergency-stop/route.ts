import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { EmploymentApi } from '@/lib/api/generated/apis/EmploymentApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';

async function POSTHandler(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ error: 'UNAUTHENTICATED' }, { status: 401 });

  const body = (await readRequestJson(request)) as {
    contractId?: string;
    activeSessionIds?: string[];
  };
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
    logServerFailure('web.emergency.stop.request_failed', error);
    if (error instanceof ResponseError) {
      const payload = await readServerResponse(error.response, 'web.emergency.stop.response_invalid', {
        error: 'STOP_RESPONSE_UNREADABLE',
      });
      return NextResponse.json(payload, { status: error.response.status });
    }
    return NextResponse.json({ error: 'STOP_RESPONSE_UNREADABLE' }, { status: 503 });
  }
}

export const POST = withServerFailureBoundary('web.emergency.stop.post_failed', POSTHandler);
