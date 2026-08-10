// Implements: architecture/reference/ux/wc-034-implementation-decomposition.md §F3 Conversation Core
// Constitutional basis: C-023 (Evidence First), C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { NextRequest, NextResponse } from 'next/server';
import { conversationProblem, createConversationApi } from '@/lib/api/conversation';
import { accessTokenFromRequest } from '@/lib/server-auth';

type CommandBody = Record<string, unknown> & { action?: unknown };

class InvalidConversationRequest extends Error {}

function requiredString(body: CommandBody, name: string): string {
  const value = body[name];
  if (typeof value !== 'string' || value.length === 0) throw new InvalidConversationRequest();
  return value;
}

function optionalQuery(request: NextRequest, name: string): string | undefined {
  return request.nextUrl.searchParams.get(name) ?? undefined;
}

function sessionRequired() {
  return NextResponse.json(
    { code: 'CONVERSATION_SESSION_REQUIRED', title: 'Secure sign in is required.' },
    { status: 401 },
  );
}

export async function GET(request: NextRequest, { params }: { params: { relationshipId: string } }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return sessionRequired();

  const cursor = optionalQuery(request, 'cursor');
  const afterCursor = optionalQuery(request, 'afterCursor');
  if (cursor && afterCursor) {
    return NextResponse.json(
      { code: 'CONVERSATION_REQUEST_INVALID', title: 'Conversation request is invalid.' },
      { status: 400 },
    );
  }

  try {
    const requestedLimit = optionalQuery(request, 'limit');
    const limit = requestedLimit ? Number.parseInt(requestedLimit, 10) : undefined;
    if (limit !== undefined && (!Number.isInteger(limit) || limit < 1 || limit > 100)) {
      throw new InvalidConversationRequest();
    }
    const page = await createConversationApi(accessToken).listConversationMessages({
      relationshipId: params.relationshipId,
      cursor,
      afterCursor,
      limit,
    });
    return NextResponse.json(page, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    if (error instanceof InvalidConversationRequest) {
      return NextResponse.json(
        { code: 'CONVERSATION_REQUEST_INVALID', title: 'Conversation request is invalid.' },
        { status: 400 },
      );
    }
    const problem = await conversationProblem(error);
    return NextResponse.json(problem.body, { status: problem.status, headers: { 'Cache-Control': 'no-store' } });
  }
}

export async function POST(request: NextRequest, { params }: { params: { relationshipId: string } }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return sessionRequired();

  try {
    const body = await request.json() as CommandBody;
    const action = requiredString(body, 'action');
    const idempotencyKey = requiredString(body, 'idempotencyKey');
    const api = createConversationApi(accessToken);

    switch (action) {
      case 'send':
        return NextResponse.json(await api.sendConversationMessage({
          relationshipId: params.relationshipId,
          idempotencyKey,
          sendConversationMessageRequestV1: {
            schemaVersion: '1.0',
            clientMessageId: requiredString(body, 'clientMessageId'),
            content: [{ schemaVersion: '1.0', blockType: 'TEXT', text: requiredString(body, 'text') }],
            locale: requiredString(body, 'locale'),
            expectedCursor: typeof body.expectedCursor === 'string' ? body.expectedCursor : undefined,
          },
        }));
      case 'retry':
        return NextResponse.json(await api.retryConversationMessage({
          relationshipId: params.relationshipId,
          messageId: requiredString(body, 'messageId'),
          idempotencyKey,
        }));
      case 'read':
        return NextResponse.json(await api.updateConversationReadPosition({
          relationshipId: params.relationshipId,
          idempotencyKey,
          updateConversationReadPositionRequestV1: {
            schemaVersion: '1.0',
            lastVisibleMessageId: requiredString(body, 'lastVisibleMessageId'),
            authoritativeCursor: requiredString(body, 'authoritativeCursor'),
          },
        }));
      case 'cancel':
        return NextResponse.json(await api.cancelConversationExecution({
          relationshipId: params.relationshipId,
          executionId: requiredString(body, 'executionId'),
          idempotencyKey,
        }));
      default:
        throw new InvalidConversationRequest();
    }
  } catch (error) {
    if (error instanceof InvalidConversationRequest || error instanceof SyntaxError) {
      return NextResponse.json(
        { code: 'CONVERSATION_REQUEST_INVALID', title: 'Conversation request is invalid.' },
        { status: 400 },
      );
    }
    const problem = await conversationProblem(error);
    return NextResponse.json(problem.body, { status: problem.status, headers: { 'Cache-Control': 'no-store' } });
  }
}