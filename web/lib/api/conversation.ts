import 'server-only';

// Implements: architecture/reference/components/conversation-core.md §3 Public Business Platform Contract
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { ConversationApi } from '@/lib/api/generated/apis/ConversationApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export function createConversationApi(accessToken: string): ConversationApi {
  return new ConversationApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
}

export async function conversationProblem(error: unknown): Promise<{ status: number; body: unknown }> {
  if (error instanceof ResponseError) {
    const body = await error.response.json().catch(() => undefined);
    return {
      status: error.response.status,
      body: body ?? { code: 'CONVERSATION_EXECUTION_UNAVAILABLE', title: 'Conversation request could not be completed.' },
    };
  }
  return {
    status: 503,
    body: { code: 'CONVERSATION_EXECUTION_UNAVAILABLE', title: 'Conversation request could not be completed.' },
  };
}

export async function openConversationStream(
  relationshipId: string,
  accessToken: string,
  lastEventId: string | null,
  signal: AbortSignal,
): Promise<Response> {
  const headers = new Headers({
    Accept: 'text/event-stream',
    Authorization: `Bearer ${accessToken}`,
  });
  if (lastEventId) headers.set('Last-Event-ID', lastEventId);

  return fetch(
    `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/conversation/stream`,
    { cache: 'no-store', headers, signal },
  );
}