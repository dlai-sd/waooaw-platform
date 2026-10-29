import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { ConfigurationApi } from '@/lib/api/generated/apis/ConfigurationApi';
import type { RelationshipOnboardRequestV1 } from '@/lib/api/generated/models/RelationshipOnboardRequestV1';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

async function PUTHandler(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  const body = (await readRequestJson(request)) as {
    onboard?: RelationshipOnboardRequestV1;
    idempotencyKey?: string;
  };
  if (!body.onboard || !body.idempotencyKey)
    return NextResponse.json({ title: 'Onboard request is invalid.' }, { status: 400 });
  try {
    const configuration = await new ConfigurationApi(
      new Configuration({ basePath: businessPlatformUrl, accessToken })
    ).updateRelationshipOnboard(
      {
        relationshipId,
        idempotencyKey: body.idempotencyKey,
        relationshipOnboardRequestV1: body.onboard,
      },
      { cache: 'no-store' }
    );
    return NextResponse.json(configuration, {
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    logServerFailure('web.relationships.relationshipid.onboard.request_failed', error);
    if (error instanceof ResponseError) {
      const payload = await readServerResponse(
        error.response,
        'web.relationships.relationshipid.onboard.response_invalid',
        { title: 'Onboard settings could not be saved.' }
      );
      return NextResponse.json(payload, {
        status: error.response.status,
        headers: { 'Cache-Control': 'no-store' },
      });
    }
    return NextResponse.json(
      { title: 'Onboard settings could not be saved.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

export const PUT = withServerFailureBoundary('web.relationships.relationshipid.onboard.put_failed', PUTHandler);
