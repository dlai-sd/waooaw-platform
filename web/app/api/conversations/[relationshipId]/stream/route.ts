// Implements: architecture/reference/components/conversation-core.md §3.3 Stream
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { NextRequest, NextResponse } from 'next/server';
import { openConversationStream } from '@/lib/api/conversation';
import { accessTokenFromRequest } from '@/lib/server-auth';

export const dynamic = 'force-dynamic';

function streamProblem(status: number) {
  if (status === 410) {
    return { code: 'CONVERSATION_CURSOR_EXPIRED', title: 'Conversation stream history expired. Reconcile the timeline.' };
  }
  if (status === 423) {
    return { code: 'CONVERSATION_STOPPED', title: 'Conversation execution is stopped.' };
  }
  return { code: 'CONVERSATION_EXECUTION_UNAVAILABLE', title: 'Conversation stream is unavailable.' };
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) {
    return NextResponse.json(
      { code: 'CONVERSATION_SESSION_REQUIRED', title: 'Secure sign in is required.' },
      { status: 401 },
    );
  }
  const { relationshipId } = await params;

  try {
    const upstream = await openConversationStream(
      relationshipId,
      accessToken,
      request.headers.get('Last-Event-ID'),
      request.signal,
    );
    if (!upstream.ok || !upstream.body) {
      const status = upstream.status >= 400 && upstream.status < 600 ? upstream.status : 503;
      return NextResponse.json(
        streamProblem(status),
        { status, headers: { 'Cache-Control': 'no-store' } },
      );
    }

    return new Response(upstream.body, {
      status: 200,
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'Content-Type': 'text/event-stream; charset=utf-8',
        Connection: 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    });
  } catch {
    return NextResponse.json(
      { code: 'CONVERSATION_EXECUTION_UNAVAILABLE', title: 'Conversation stream is unavailable.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } },
    );
  }
}