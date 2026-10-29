import 'server-only';
import { correlateFailureBody, logServerFailure, readServerResponse } from '@/lib/server-failure';

// Implements: architecture/reference/components/conversation-core.md §3 Public Business Platform Contract
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { ConversationApi } from '@/lib/api/generated/apis/ConversationApi';
import { SharedConversationApi } from '@/lib/api/generated/conversation-v1/src/apis/SharedConversationApi';
import {
  Configuration as CandidateConfiguration,
  ResponseError as CandidateResponseError,
} from '@/lib/api/generated/conversation-v1/src/runtime';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export function createConversationApi(accessToken: string): ConversationApi {
  return new ConversationApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
}

export function createCanonicalConversationApi(accessToken: string): SharedConversationApi {
  return new SharedConversationApi(new CandidateConfiguration({ basePath: businessPlatformUrl, accessToken }));
}

export async function conversationProblem(error: unknown): Promise<{ status: number; body: unknown }> {
  const correlationId = logServerFailure('web.conversation.request_failed', error);
  if (error instanceof ResponseError || error instanceof CandidateResponseError) {
    const body = await readServerResponse(error.response, 'web.api.conversation.response_invalid', undefined);
    return {
      status: error.response.status,
      body:
        error.response.status >= 500
          ? correlateFailureBody(
              body ?? {
                code: 'CONVERSATION_EXECUTION_UNAVAILABLE',
                title: 'Conversation request could not be completed.',
              },
              correlationId
            )
          : (body ?? {
              code: 'CONVERSATION_EXECUTION_UNAVAILABLE',
              title: 'Conversation request could not be completed.',
            }),
    };
  }
  return {
    status: 503,
    body: {
      code: 'CONVERSATION_EXECUTION_UNAVAILABLE',
      title: 'Conversation request could not be completed.',
      correlationId,
    },
  };
}

export async function openConversationStream(
  relationshipId: string,
  accessToken: string,
  lastEventId: string | null,
  signal: AbortSignal
): Promise<Response> {
  const headers = new Headers({
    Accept: 'text/event-stream',
    Authorization: `Bearer ${accessToken}`,
  });
  if (lastEventId) headers.set('Last-Event-ID', lastEventId);

  return fetch(
    `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/conversation/${
      process.env.WC120_CONVERSATION_ENABLED === 'true' ? 'events' : 'stream'
    }`,
    { cache: 'no-store', headers, signal }
  );
}
