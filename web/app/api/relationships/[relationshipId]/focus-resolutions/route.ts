import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { RelationshipWorkspaceApi } from '@/lib/api/generated/apis/RelationshipWorkspaceApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

async function POSTHandler(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  const body = (await readRequestJson(request).catch(() => undefined)) as { focusToken?: unknown } | undefined;
  if (typeof body?.focusToken !== 'string' || body.focusToken.length > 2048)
    return NextResponse.json({ title: 'Focus reference is invalid.' }, { status: 400 });
  try {
    const resolution = await new RelationshipWorkspaceApi(
      new Configuration({ basePath: businessPlatformUrl, accessToken })
    ).resolveWorkspaceFocus(
      {
        relationshipId,
        resolveWorkspaceFocusRequestV1: { focusToken: body.focusToken },
      },
      { cache: 'no-store' }
    );
    return NextResponse.json(resolution, {
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    logServerFailure('web.relationships.relationshipid.focus.resolutions.request_failed', error);
    if (error instanceof ResponseError) {
      const payload = await readServerResponse(
        error.response,
        'web.relationships.relationshipid.focus.resolutions.response_invalid',
        { title: 'Focus could not be confirmed.' }
      );
      return NextResponse.json(payload, {
        headers: { 'Cache-Control': 'no-store' },
        status: error.response.status,
      });
    }
    return NextResponse.json(
      { title: 'Focus could not be confirmed.' },
      { headers: { 'Cache-Control': 'no-store' }, status: 503 }
    );
  }
}

export const POST = withServerFailureBoundary(
  'web.relationships.relationshipid.focus.resolutions.post_failed',
  POSTHandler
);
