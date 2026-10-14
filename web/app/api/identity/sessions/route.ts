import { type NextRequest, NextResponse } from 'next/server';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { listSessions, revokeAllSessions } from '@/lib/web-session-store';

export async function GET(request: NextRequest) {
  const token = await sessionTokenFromRequest(request);
  if (!token)
    return NextResponse.json(
      { title: 'Secure sign in is required.' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  try {
    return NextResponse.json({ sessions: await listSessions(token) }, { headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return NextResponse.json(
      {
        code: 'SESSION_STORE_UNAVAILABLE',
        title: 'Session management is temporarily unavailable.',
      },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

export async function DELETE(request: NextRequest) {
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
  } catch {
    return NextResponse.json(
      {
        code: 'SESSION_STORE_UNAVAILABLE',
        title: 'Session revocation could not be confirmed.',
      },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}
