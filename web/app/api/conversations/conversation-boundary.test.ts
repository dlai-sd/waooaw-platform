/** @jest-environment node */

import { NextRequest } from 'next/server';

const accessTokenFromRequest = jest.fn();
const listConversationMessages = jest.fn();
const sendConversationMessage = jest.fn();
const openConversationStream = jest.fn();

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest }));
jest.mock('@/lib/api/conversation', () => ({
  conversationProblem: jest.fn(async () => ({ status: 503, body: { code: 'CONVERSATION_EXECUTION_UNAVAILABLE' } })),
  createConversationApi: jest.fn(() => ({
    listConversationMessages,
    sendConversationMessage,
    retryConversationMessage: jest.fn(),
    updateConversationReadPosition: jest.fn(),
    cancelConversationExecution: jest.fn(),
  })),
  openConversationStream,
}));

const relationshipId = '5f33925b-fb0c-4366-8414-7f85309639b9';
const params = { params: Promise.resolve({ relationshipId }) };

describe('conversation server boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    accessTokenFromRequest.mockResolvedValue('server-token');
  });

  it('requires the server session without exposing an upstream location', async () => {
    accessTokenFromRequest.mockResolvedValue(undefined);
    const { GET } = await import('./[relationshipId]/route');
    const response = await GET(new NextRequest(`http://localhost/api/conversations/${relationshipId}`), params);

    expect(response.status).toBe(401);
    expect(JSON.stringify(await response.json())).not.toMatch(/localhost:5001|server-token|tenant/i);
    expect(listConversationMessages).not.toHaveBeenCalled();
  });

  it('forwards timeline cursors through the authenticated generated client', async () => {
    listConversationMessages.mockResolvedValue({ schemaVersion: '1.0', items: [], authoritativeCursor: 'cursor', hasMore: false });
    const { GET } = await import('./[relationshipId]/route');
    const response = await GET(new NextRequest(`http://localhost/api/conversations/${relationshipId}?afterCursor=prior&limit=40`), params);

    expect(response.status).toBe(200);
    expect(listConversationMessages).toHaveBeenCalledWith({ relationshipId, cursor: undefined, afterCursor: 'prior', limit: 40 });
    expect(response.headers.get('Cache-Control')).toBe('no-store');
  });

  it('keeps send identity and content inside the server-side generated call', async () => {
    sendConversationMessage.mockResolvedValue({ outcome: 'ACCEPTED' });
    const { POST } = await import('./[relationshipId]/route');
    const request = new NextRequest(`http://localhost/api/conversations/${relationshipId}`, {
      method: 'POST',
      body: JSON.stringify({
        action: 'send',
        idempotencyKey: 'f5bc4af1-bb1a-45f9-b979-71f0dfc8379e',
        clientMessageId: '51885e4d-53ac-4abf-ad77-58cd127a3dc4',
        text: 'Please summarize today.',
        locale: 'en-IN',
        expectedCursor: 'authoritative-cursor',
      }),
    });
    const response = await POST(request, params);

    expect(response.status).toBe(200);
    expect(sendConversationMessage).toHaveBeenCalledWith(expect.objectContaining({
      relationshipId,
      idempotencyKey: 'f5bc4af1-bb1a-45f9-b979-71f0dfc8379e',
      sendConversationMessageRequestV1: expect.objectContaining({ clientMessageId: '51885e4d-53ac-4abf-ad77-58cd127a3dc4' }),
    }));
  });

  it('proxies SSE with resume identity and strips upstream private headers', async () => {
    openConversationStream.mockResolvedValue(new Response('event: heartbeat\ndata: {}\n\n', {
      headers: { 'Content-Type': 'text/event-stream', 'X-Internal-Provider': 'private' },
    }));
    const { GET } = await import('./[relationshipId]/stream/route');
    const request = new NextRequest(`http://localhost/api/conversations/${relationshipId}/stream`, {
      headers: { 'Last-Event-ID': 'event-17' },
    });
    const response = await GET(request, params);

    expect(openConversationStream).toHaveBeenCalledWith(relationshipId, 'server-token', 'event-17', expect.any(AbortSignal));
    expect(response.headers.get('Content-Type')).toContain('text/event-stream');
    expect(response.headers.get('X-Internal-Provider')).toBeNull();
    expect(response.headers.get('Cache-Control')).toContain('no-store');
  });

  it.each([
    [410, 'CONVERSATION_CURSOR_EXPIRED'],
    [423, 'CONVERSATION_STOPPED'],
  ])('preserves canonical stream status %s without exposing upstream details', async (status, code) => {
    openConversationStream.mockResolvedValue(new Response(JSON.stringify({ secret: 'upstream detail' }), { status }));
    const { GET } = await import('./[relationshipId]/stream/route');
    const response = await GET(new NextRequest(`http://localhost/api/conversations/${relationshipId}/stream`), params);

    expect(response.status).toBe(status);
    expect(await response.json()).toEqual(expect.objectContaining({ code }));
    expect(response.headers.get('Cache-Control')).toBe('no-store');
  });
});