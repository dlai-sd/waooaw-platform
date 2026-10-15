import { type NextRequest, NextResponse } from 'next/server';
import { sessionTokenFromRequest } from '@/lib/server-auth';
import { revokeOneSession } from '@/lib/web-session-store';

export async function DELETE(request: NextRequest, context: { params: Promise<{ sessionId: string }> }) {
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
