// Implements: WC-134 R005; identity-boundary.md Section 6.3.
// Constitutional basis: C-023, C-026, C-059, C-063

import { type NextRequest, NextResponse } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { enforceAuthAbuse } from '@/lib/auth-abuse-limiter';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { RelationshipWorkspaceApi } from '@/lib/api/generated/apis/RelationshipWorkspaceApi';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { logServerFailure } from '@/lib/server-failure';
import { readRequestJson, withServerFailureBoundary } from '@/lib/server-failure-boundary';

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const headers = { 'Cache-Control': 'no-store' };
const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

function problem(status: number, code: string) {
  return NextResponse.json({ code }, { status, headers });
}

async function POSTHandler(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  if (!isSameOriginRequest(request, process.env.NEXTAUTH_URL ?? request.nextUrl.origin))
    return problem(403, 'IDENTITY_ACTION_DENIED');
  const limited = await enforceAuthAbuse(request, 'PROVIDER_LINK');
  if (limited) return limited;
  const session = await sessionTokenFromRequest(request);
  const accessToken = session ? activeAccessToken(session) : undefined;
  if (!accessToken) return problem(401, 'IDENTITY_SESSION_REQUIRED');

  const { relationshipId } = await params;
  if (!uuid.test(relationshipId)) return problem(400, 'RELATIONSHIP_WORKSPACE_REQUEST_INVALID');
  const body = await readRequestJson(request);
  if (
    body === null ||
    typeof body !== 'object' ||
    !('identityAccountLinkId' in body) ||
    typeof body.identityAccountLinkId !== 'string' ||
    !uuid.test(body.identityAccountLinkId) ||
    !('consentToRelationshipChannel' in body) ||
    body.consentToRelationshipChannel !== true ||
    Object.keys(body).some((key) => !['identityAccountLinkId', 'consentToRelationshipChannel'].includes(key))
  )
    return problem(400, 'WHATSAPP_CHANNEL_CONSENT_REQUIRED');

  try {
    const api = new RelationshipWorkspaceApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
    const result = await api.attachRelationshipWhatsAppChannel(
      {
        relationshipId,
        attachWhatsAppChannelRequestV1: {
          identityAccountLinkId: body.identityAccountLinkId,
          consentToRelationshipChannel: true,
        },
      },
      { cache: 'no-store' }
    );
    return NextResponse.json(result, { headers });
  } catch (error) {
    logServerFailure('web.relationships.whatsapp_channel.owner_failed', error);
    if (!(error instanceof ResponseError)) throw error;
    const status = error.response.status;
    const codes: Record<number, string> = {
      400: 'WHATSAPP_CHANNEL_CONSENT_REQUIRED',
      401: 'IDENTITY_SESSION_REQUIRED',
      403: 'IDENTITY_ACTION_DENIED',
      404: 'IDENTITY_RESOURCE_NOT_ACCESSIBLE',
      409: 'RELATIONSHIP_IDEMPOTENCY_CONFLICT',
      423: 'RELATIONSHIP_WORKSPACE_BLOCKED',
      503: 'WHATSAPP_CHANNEL_BINDING_UNAVAILABLE',
    };
    if (status === 403) {
      const payload: unknown = await error.response.json();
      if (
        payload !== null &&
        typeof payload === 'object' &&
        'code' in payload &&
        payload.code === 'IDENTITY_STEP_UP_REQUIRED'
      )
        return problem(403, 'IDENTITY_STEP_UP_REQUIRED');
    }
    return problem(status in codes ? status : 503, codes[status] ?? 'WHATSAPP_CHANNEL_BINDING_UNAVAILABLE');
  }
}

export const POST = withServerFailureBoundary('web.relationships.whatsapp_channel.post_failed', POSTHandler);
