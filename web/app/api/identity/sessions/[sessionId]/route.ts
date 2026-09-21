import { type NextRequest, NextResponse } from 'next/server';
import { identityProblem, revokeIdentitySession } from '@/lib/api/identity';
import { accessTokenFromRequest } from '@/lib/server-auth';

export async function DELETE(request: NextRequest, context: { params: Promise<{ sessionId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const idempotencyKey = request.headers.get('Idempotency-Key');
  if (!idempotencyKey) return NextResponse.json({ title: 'Session request is invalid.' }, { status: 400 });
  try {
    const { sessionId } = await context.params;
    return NextResponse.json(await revokeIdentitySession(accessToken, sessionId, idempotencyKey), {
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    const problem = await identityProblem(error);
    return NextResponse.json(problem.body, { status: problem.status, headers: { 'Cache-Control': 'no-store' } });
  }
}
