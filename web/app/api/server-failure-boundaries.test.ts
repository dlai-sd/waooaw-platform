/** @jest-environment node */

import { NextRequest } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { POST as postAcquisitionEvent } from './acquisition/events/route';
import { POST as postPortalInteraction } from './interactions/portal/route';
import { createConversationApi } from '@/lib/api/conversation';
import { POST as postHireSetup } from './relationships/[relationshipId]/hire-setup/route';
import { GET as streamConversation } from './conversations/[relationshipId]/stream/route';
import { openConversationStream } from '@/lib/api/conversation';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/api/conversation', () => ({
  ...jest.requireActual('@/lib/api/conversation'),
  createConversationApi: jest.fn(),
  openConversationStream: jest.fn(),
}));

const params = { params: Promise.resolve({ relationshipId: 'relationship-1' }) };

beforeEach(() => {
  jest.spyOn(console, 'error').mockImplementation();
  jest.mocked(accessTokenFromRequest).mockResolvedValue('server-token');
});
afterEach(() => jest.restoreAllMocks());

function logs() {
  return jest.mocked(console.error).mock.calls.map(([record]) => JSON.parse(record));
}

it('keeps invalid user input silent', async () => {
  const response = await postAcquisitionEvent(
    new Request('https://web.example/api/acquisition/events', {
      method: 'POST',
      body: 'not json',
    })
  );
  expect(response.status).toBe(400);
  expect(logs()).toEqual([]);
});

it('does not mistake a portal network TypeError for invalid user input', async () => {
  jest.mocked(createConversationApi).mockReturnValue({
    sendPortalInteractionMessage: jest.fn().mockRejectedValue(new TypeError('fetch failed')),
  } as never);
  const response = await postPortalInteraction(
    new NextRequest('https://web.example/api/interactions/portal', {
      method: 'POST',
      body: JSON.stringify({
        idempotencyKey: 'key-1',
        clientMessageId: 'message-1',
        text: 'Customer private text',
        locale: 'en-IN',
        currentSurface: 'MY_AGENTS',
      }),
    })
  );
  expect(response.status).toBe(503);
  const body = await response.json();
  expect(body.correlationId).toBe(response.headers.get('x-correlation-id'));
  expect(logs()[0]).toMatchObject({
    event: 'web.conversation.request_failed',
    correlationId: body.correlationId,
    error: { type: 'TypeError', reason: 'FETCH_FAILED' },
  });
  expect(JSON.stringify(logs())).not.toContain('Customer private text');
});

it.each(['transport', 'upstream-5xx', 'malformed-success'])('correlates hire setup %s failures', async (failure) => {
  const fetcher = jest.spyOn(globalThis, 'fetch');
  if (failure === 'transport') fetcher.mockRejectedValue(new Error('private upstream'));
  else
    fetcher.mockResolvedValue(
      new Response(
        failure === 'malformed-success'
          ? 'private response'
          : JSON.stringify({ title: 'Unavailable', correlationId: 'backend-123' }),
        { status: failure === 'malformed-success' ? 200 : 502 }
      )
    );
  const response = await postHireSetup(
    new NextRequest('https://web.example/api/relationships/rel/hire-setup', {
      method: 'POST',
      headers: { 'Idempotency-Key': 'key-1' },
      body: '{}',
    }),
    params
  );
  expect(response.status).toBe(failure === 'upstream-5xx' ? 502 : 503);
  const body = await response.json();
  expect(body.correlationId).toBe(response.headers.get('x-correlation-id'));
  expect(logs().every((record) => record.correlationId === body.correlationId)).toBe(true);
  if (failure === 'upstream-5xx') expect(logs()[0].upstreamCorrelationId).toBe('backend-123');
  expect(JSON.stringify(logs())).not.toMatch(/private upstream|private response/);
});

it('passes successful SSE through without consuming the stream', async () => {
  jest.mocked(openConversationStream).mockResolvedValue(new Response('data: hello\n\n'));
  const response = await streamConversation(
    new NextRequest('https://web.example/api/conversations/rel/stream'),
    params
  );
  expect(response.status).toBe(200);
  expect(response.headers.get('content-type')).toContain('text/event-stream');
  expect(await response.text()).toBe('data: hello\n\n');
  expect(logs()).toEqual([]);
});
