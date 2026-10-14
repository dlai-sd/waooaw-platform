import { type NextRequest, NextResponse } from 'next/server';
import { RelationshipWorkspaceApi } from '@/lib/api/generated/apis/RelationshipWorkspaceApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export async function POST(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  const body = (await request.json().catch(() => undefined)) as { focusToken?: unknown } | undefined;
  if (typeof body?.focusToken !== 'string' || body.focusToken.length > 2048)
    return NextResponse.json({ title: 'Focus reference is invalid.' }, { status: 400 });
  try {
    const resolution = await new RelationshipWorkspaceApi(
      new Configuration({ basePath: businessPlatformUrl, accessToken })
    ).resolveWorkspaceFocus(
      { relationshipId, resolveWorkspaceFocusRequestV1: { focusToken: body.focusToken } },
      { cache: 'no-store' }
    );
    return NextResponse.json(resolution, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    if (error instanceof ResponseError) {
      const payload = await error.response.json().catch(() => ({ title: 'Focus could not be confirmed.' }));
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
