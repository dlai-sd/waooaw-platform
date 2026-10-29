import { withServerFailureBoundary, readRequestJson, InvalidRequestJson } from '@/lib/server-failure-boundary';
// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// Constitutional basis: C-026 (Tenant Isolation), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { type NextRequest, NextResponse } from 'next/server';
import { conversationProblem, createConversationApi } from '@/lib/api/conversation';
import type { PortalInteractionSurfaceV1 } from '@/lib/api/generated/models/PortalInteractionSurfaceV1';
import { accessTokenFromRequest } from '@/lib/server-auth';

const surfaces = new Set<PortalInteractionSurfaceV1>([
  'MARKETPLACE',
  'MY_AGENTS',
  'ALERTS',
  'RELATIONSHIP',
  'PERFORMANCE',
  'BILLING',
  'SETTINGS',
  'PROFILE',
]);

class InvalidPortalRequest extends Error {}

function sessionRequired() {
  return NextResponse.json(
    {
      code: 'PORTAL_INTERACTION_SESSION_REQUIRED',
      title: 'Secure sign in is required.',
    },
    { status: 401 }
  );
}

async function GETHandler(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return sessionRequired();
  const cursor = request.nextUrl.searchParams.get('cursor') ?? undefined;
  const limitText = request.nextUrl.searchParams.get('limit');
  const limit = limitText ? Number.parseInt(limitText, 10) : undefined;
  if (limit !== undefined && (!Number.isInteger(limit) || limit < 1 || limit > 100)) {
    return NextResponse.json(
      {
        code: 'PORTAL_INTERACTION_REQUEST_INVALID',
        title: 'Portal interaction request is invalid.',
      },
      { status: 400 }
    );
  }
  try {
    const page = await createConversationApi(accessToken).listPortalInteractionMessages({ cursor, limit });
    return NextResponse.json(page, {
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    const problem = await conversationProblem(error);
    return NextResponse.json(problem.body, {
      status: problem.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  }
}

async function POSTHandler(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return sessionRequired();
  try {
    const body = (await readRequestJson(request)) as Record<string, unknown>;
    if (
      typeof body.idempotencyKey !== 'string' ||
      typeof body.clientMessageId !== 'string' ||
      typeof body.text !== 'string' ||
      !body.text.trim() ||
      typeof body.locale !== 'string' ||
      typeof body.currentSurface !== 'string' ||
      !surfaces.has(body.currentSurface as PortalInteractionSurfaceV1)
    ) {
      throw new InvalidPortalRequest('Invalid portal interaction request.');
    }
    const result = await createConversationApi(accessToken).sendPortalInteractionMessage({
      idempotencyKey: body.idempotencyKey,
      sendPortalInteractionMessageRequestV1: {
        schemaVersion: '1.0',
        clientMessageId: body.clientMessageId,
        content: [{ schemaVersion: '1.0', blockType: 'TEXT', text: body.text }],
        locale: body.locale,
        currentSurface: body.currentSurface as PortalInteractionSurfaceV1,
        expectedCursor: typeof body.expectedCursor === 'string' ? body.expectedCursor : undefined,
      },
    });
    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    if (error instanceof InvalidPortalRequest || error instanceof InvalidRequestJson) {
      return NextResponse.json(
        {
          code: 'PORTAL_INTERACTION_REQUEST_INVALID',
          title: 'Portal interaction request is invalid.',
        },
        { status: 400 }
      );
    }
    const problem = await conversationProblem(error);
    return NextResponse.json(problem.body, {
      status: problem.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  }
}

export const GET = withServerFailureBoundary('web.interactions.portal.get_failed', GETHandler);
export const POST = withServerFailureBoundary('web.interactions.portal.post_failed', POSTHandler);
