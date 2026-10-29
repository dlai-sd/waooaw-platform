import { logServerFailure } from '@/lib/server-failure';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { listSessions, revokeAllSessions } from '@/lib/web-session-store';

async function GETHandler(request: NextRequest) {
  const token = await sessionTokenFromRequest(request);
  if (!token)
    return NextResponse.json(
      { title: 'Secure sign in is required.' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  try {
    return NextResponse.json({ sessions: await listSessions(token) }, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    logServerFailure('web.identity.sessions.list_failed', error);
    return NextResponse.json(
      {
        code: 'SESSION_STORE_UNAVAILABLE',
        title: 'Session management is temporarily unavailable.',
      },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

async function DELETEHandler(request: NextRequest) {
  const token = await sessionTokenFromRequest(request);
  if (!token)
    return NextResponse.json(
      { title: 'Secure sign in is required.' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  const idempotencyKey = request.headers.get('Idempotency-Key');
  if (!idempotencyKey)
    return NextResponse.json(
      { title: 'Session request is invalid.' },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  try {
    return NextResponse.json(
      {
        scope: 'ALL',
        revokedCount: await revokeAllSessions(token, 'CUSTOMER_REVOKED_ALL'),
      },
      { headers: { 'Cache-Control': 'no-store' } }
    );
  } catch (error) {
    logServerFailure('web.identity.sessions.revoke_all_failed', error);
    return NextResponse.json(
      {
        code: 'SESSION_STORE_UNAVAILABLE',
        title: 'Session revocation could not be confirmed.',
      },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

export const GET = withServerFailureBoundary('web.identity.sessions.get_failed', GETHandler);
export const DELETE = withServerFailureBoundary('web.identity.sessions.delete_failed', DELETEHandler);
