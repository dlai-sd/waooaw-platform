import { logServerFailure } from '@/lib/server-failure';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { revokeOneSession } from '@/lib/web-session-store';

async function DELETEHandler(request: NextRequest, context: { params: Promise<{ sessionId: string }> }) {
  const token = await sessionTokenFromRequest(request);
  if (!token)
    return NextResponse.json(
      { title: 'Secure sign in is required.' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  const idempotencyKey = request.headers.get('Idempotency-Key');
  if (!idempotencyKey) return NextResponse.json({ title: 'Session request is invalid.' }, { status: 400 });
  try {
    const { sessionId } = await context.params;
    const revokedCount = await revokeOneSession(token, sessionId);
    if (revokedCount < 0)
      return NextResponse.json(
        { code: 'IDENTITY_RESOURCE_NOT_ACCESSIBLE' },
        { status: 404, headers: { 'Cache-Control': 'no-store' } }
      );
    return NextResponse.json({ scope: 'ONE', revokedCount }, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    logServerFailure('web.identity.sessions.sessionid.request_failed', error);
    return NextResponse.json(
      {
        code: 'SESSION_STORE_UNAVAILABLE',
        title: 'Session revocation could not be confirmed.',
      },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

export const DELETE = withServerFailureBoundary('web.identity.sessions.sessionid.delete_failed', DELETEHandler);
