import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { TextDecoder as NodeTextDecoder } from 'node:util';
import type { ConversationMessageV1 } from '@/lib/api/generated/models/ConversationMessageV1';
import { ConversationExperience } from './ConversationExperience';

const relationshipId = '5f33925b-fb0c-4366-8414-7f85309639b9';
const messageId = '4d492966-4015-40a8-b743-cc660735b1e0';

type FetchMock = jest.Mock<Promise<Response>, [RequestInfo | URL, RequestInit?]>;

function streamEvent(eventType: string, overrides: Record<string, unknown> = {}) {
  return {
    schemaVersion: '1.0',
    eventId: `event-${eventType}`,
    eventType,
    relationshipId,
    sequence: 2,
    occurredAt: '2026-08-10T10:01:00Z',
    data: eventType === 'heartbeat' ? { serverTime: '2026-08-10T10:01:00Z' } : {},
    ...overrides,
  };
}

function pendingStream(signal?: AbortSignal | null, events: unknown[] = []) {
  const queued = events.map((event) => Buffer.from(`data: ${JSON.stringify(event)}\n\n`));
  let pending: { resolve: (result: ReadableStreamReadResult<Uint8Array>) => void; reject: (reason: unknown) => void } | undefined;
  signal?.addEventListener('abort', () => pending?.reject(new DOMException('Aborted', 'AbortError')), { once: true });
  return {
    response: {
      ok: true,
      status: 200,
      body: {
        getReader: () => ({
          read: () => {
            const value = queued.shift();
            if (value) return Promise.resolve({ done: false as const, value });
            return new Promise<ReadableStreamReadResult<Uint8Array>>((resolve, reject) => { pending = { resolve, reject }; });
          },
        }),
      },
    } as Response,
    push(event: unknown) {
      const value = Buffer.from(`data: ${JSON.stringify(event)}\n\n`);
      if (pending) {
        const reader = pending;
        pending = undefined;
        reader.resolve({ done: false, value });
      } else {
        queued.push(value);
      }
    },
  };
}

function streamResponse(signal?: AbortSignal | null, events: unknown[] = []) {
  return pendingStream(signal, events).response;
}

function statusResponse(status: number) {
  return { ok: false, status, body: undefined } as unknown as Response;
}

function installFetch(
  apiHandler: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>,
  streamHandler: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> = async (_input, init) => streamResponse(init?.signal),
): FetchMock {
  const mock = jest.fn((input: RequestInfo | URL, init?: RequestInit) => (
    String(input).endsWith('/stream') ? streamHandler(input, init) : apiHandler(input, init)
  )) as FetchMock;
  global.fetch = mock;
  return mock;
}

function apiCalls(mock: FetchMock) {
  return mock.mock.calls.filter(([input]) => !String(input).endsWith('/stream'));
}

function streamCalls(mock: FetchMock) {
  return mock.mock.calls.filter(([input]) => String(input).endsWith('/stream'));
}

function controllableStream() {
  let stream: ReturnType<typeof pendingStream> | undefined;
  return {
    response(signal?: AbortSignal | null) {
      stream = pendingStream(signal);
      return stream.response;
    },
    push(event: unknown) {
      stream?.push(event);
    },
  };
}

const planCard = {
  schemaVersion: '1.0' as const,
  cardId: 'e2d02f31-b25f-46e7-bec5-a0cb206c02e1',
  cardType: 'PLAN' as const,
  owner: 'SHARED' as const,
  state: 'ACTIVE',
  effect: 'Sets the next agreed outcome.',
  commands: [{ commandId: 'VIEW_PLAN', label: 'View plan', availability: 'AVAILABLE' as const, unavailableReason: 'Plan workspace is not available in this release.' }],
  goal: 'Increase qualified enquiries',
  progressState: 'ON_TRACK',
};

const governedCards = [
  { ...planCard, cardId: 'e2d02f31-b25f-46e7-bec5-a0cb206c02e1' },
  {
    schemaVersion: '1.0' as const, cardId: 'ecb34c35-1b38-44c5-afdb-d5dac78aed9f', cardType: 'ACTION' as const,
    owner: 'CUSTOMER' as const, state: 'READY', effect: 'Starts approved customer work.', commands: [], goal: 'Approve the brief',
  },
  {
    schemaVersion: '1.0' as const, cardId: '71383a2e-6957-4108-b4dd-0739f59d6c87', cardType: 'DELIVERABLE' as const,
    owner: 'PROFESSIONAL' as const, state: 'DRAFT', effect: 'Makes the draft available for review.', commands: [],
    title: 'Campaign brief', deliverableState: 'REVIEW',
  },
  {
    schemaVersion: '1.0' as const, cardId: '7c2dbe82-da1c-42cd-8700-dad182132b99', cardType: 'DECISION' as const,
    owner: 'SHARED' as const, state: 'OPEN', effect: 'Changes the approved campaign direction.', commands: [],
    decisionState: 'CUSTOMER_INPUT_REQUIRED', authorityImpact: 'No work starts before selection.',
    alternatives: [{ alternativeId: 'A', label: 'Continue', effect: 'Uses the current approved brief.' }],
  },
];

function message(overrides: Partial<ConversationMessageV1> = {}): ConversationMessageV1 {
  return {
    schemaVersion: '1.0',
    messageId,
    relationshipId,
    sequence: 1,
    actor: 'PROFESSIONAL',
    channel: 'WEB',
    content: [{ schemaVersion: '1.0', blockType: 'TEXT', text: 'Here is the current plan.' }],
    cards: governedCards,
    deliveryState: 'ACCEPTED',
    processingState: 'RUNNING',
    evidenceState: 'PENDING',
    partial: true,
    completionReason: 'PARTIAL_FAILURE',
    acceptedAt: new Date('2026-08-10T10:00:00Z'),
    ...overrides,
  };
}

function timeline(items: ConversationMessageV1[] = [message()], overrides: Record<string, unknown> = {}) {
  return {
    schemaVersion: '1.0',
    relationshipId,
    items,
    authoritativeCursor: 'authoritative-cursor-0001',
    hasMore: false,
    serverTime: '2026-08-10T10:01:00Z',
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);
}

function setOnline(value: boolean) {
  Object.defineProperty(navigator, 'onLine', { configurable: true, value });
}

describe('ConversationExperience', () => {
  beforeEach(() => {
    localStorage.clear();
    setOnline(true);
    Object.defineProperty(global, 'TextDecoder', { configurable: true, value: NodeTextDecoder });
    Object.defineProperty(global.crypto, 'randomUUID', {
      configurable: true,
      value: jest.fn()
        .mockReturnValueOnce('51885e4d-53ac-4abf-ad77-58cd127a3dc4')
        .mockReturnValueOnce('f5bc4af1-bb1a-45f9-b979-71f0dfc8379e')
        .mockReturnValue('d075fa11-75c2-4b6e-9a87-510421293a66'),
    });
  });

  afterEach(() => jest.restoreAllMocks());

  it('renders canonical status, partial disclosure, and keyboard-operable typed cards', async () => {
    installFetch(() => jsonResponse(timeline()));
    render(<ConversationExperience relationshipId={relationshipId} />);

    expect(await screen.findByText('Here is the current plan.')).toBeVisible();
    expect(screen.getByText('Accepted by WAOOAW')).toBeVisible();
    expect(screen.getByText('Professional processing')).toBeVisible();
    expect(screen.getByText('Evidence pending')).toBeVisible();
    expect(screen.queryByText('Evidence recorded')).not.toBeInTheDocument();
    expect(screen.getByText(/Incomplete response/)).toBeVisible();
    expect(screen.getByRole('article', { name: 'plan card' })).toHaveTextContent('Increase qualified enquiries');
    expect(screen.getByRole('article', { name: 'action card' })).toHaveTextContent('Approve the brief');
    expect(screen.getByRole('article', { name: 'deliverable card' })).toHaveTextContent('Campaign brief');
    expect(screen.getByRole('article', { name: 'decision card' })).toHaveTextContent('No work starts before selection.');
    expect(screen.getByRole('button', { name: 'View plan' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'View plan' })).toHaveAttribute('title', 'Plan workspace is not available in this release.');
  });

  it('never reports recorded evidence without a non-null evidence record identity', async () => {
    installFetch(() => jsonResponse(timeline([
      message({ evidenceState: 'RECORDED', evidenceRecordId: undefined, cards: [] }),
    ])));
    render(<ConversationExperience relationshipId={relationshipId} />);

    expect(await screen.findByText('Evidence pending verification')).toBeVisible();
    expect(screen.queryByText('Evidence recorded')).not.toBeInTheDocument();
  });

  it('reconciles before sending one UUID-identified contribution through same-origin BFF', async () => {
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline([])))
      .mockImplementationOnce(() => jsonResponse(timeline([])))
      .mockImplementationOnce(() => jsonResponse({
        schemaVersion: '1.0',
        outcome: 'ACCEPTED',
        message: message({ actor: 'CUSTOMER', clientMessageId: '51885e4d-53ac-4abf-ad77-58cd127a3dc4', cards: [], partial: false }),
        executionId: '3ead2d21-f908-40b5-9510-b1e77f516d7e',
        authoritativeCursor: 'authoritative-cursor-0002',
        replayed: false,
      }));
    const requestMock = installFetch(fetchMock);
    render(<ConversationExperience relationshipId={relationshipId} />);

    const composer = await screen.findByLabelText('Message your professional');
    fireEvent.change(composer, { target: { value: 'Please summarize today.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    await waitFor(() => expect(apiCalls(requestMock)).toHaveLength(3));
    expect(apiCalls(requestMock)[1][0]).toContain('afterCursor=authoritative-cursor-0001');
    const sendCall = apiCalls(requestMock)[2];
    expect(sendCall[0]).toBe(`/api/conversations/${relationshipId}`);
    expect(sendCall[0]).not.toMatch(/5001|professional-runtime|provider/i);
    expect(JSON.parse(String(sendCall[1]?.body))).toEqual(expect.objectContaining({
      action: 'send',
      clientMessageId: '51885e4d-53ac-4abf-ad77-58cd127a3dc4',
      idempotencyKey: 'f5bc4af1-bb1a-45f9-b979-71f0dfc8379e',
      text: 'Please summarize today.',
    }));
    expect(await screen.findByRole('button', { name: 'Cancel response' })).toBeVisible();
  });

  it('retains one relationship-local offline outbox and submits it after authoritative reconciliation', async () => {
    setOnline(false);
    const fetchMock = jest.fn().mockImplementationOnce(() => jsonResponse(timeline([])));
    const requestMock = installFetch(fetchMock);
    render(<ConversationExperience relationshipId={relationshipId} />);

    fireEvent.change(await screen.findByLabelText('Message your professional'), { target: { value: 'Queue this safely.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByRole('button', { name: 'Queued' })).toBeDisabled();
    expect(apiCalls(requestMock)).toHaveLength(1);
    expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:outbox`)).toContain('Queue this safely.');

    fetchMock
      .mockImplementationOnce(() => jsonResponse(timeline([])))
      .mockImplementationOnce(() => jsonResponse({
        schemaVersion: '1.0', outcome: 'ACCEPTED', message: message({ actor: 'CUSTOMER', cards: [], partial: false }),
        authoritativeCursor: 'authoritative-cursor-0002', replayed: false,
      }));
    setOnline(true);
      await act(async () => window.dispatchEvent(new Event('online')));

    await waitFor(() => expect(apiCalls(requestMock)).toHaveLength(3));
    expect(apiCalls(requestMock)[1][0]).toContain('afterCursor=authoritative-cursor-0001');
    expect(JSON.parse(String(apiCalls(requestMock)[2][1]?.body))).toEqual(expect.objectContaining({
      idempotencyKey: 'f5bc4af1-bb1a-45f9-b979-71f0dfc8379e',
      text: 'Queue this safely.',
    }));
    await waitFor(() => expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:outbox`)).toBeNull());
  });

  it('reuses the original retry identity only after timeline reconciliation', async () => {
    const unresolved = message({ deliveryState: 'UNRESOLVED', processingState: 'FAILED', cards: [], partial: false });
    localStorage.setItem(`waooaw:conversation:${relationshipId}:retry:${messageId}`, 'original-idempotency-key');
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline([unresolved])))
      .mockImplementationOnce(() => jsonResponse(timeline([unresolved])))
      .mockImplementationOnce(() => jsonResponse({
        schemaVersion: '1.0', outcome: 'REPLAYED', message: unresolved,
        authoritativeCursor: 'authoritative-cursor-0001', replayed: true,
      }));
    const requestMock = installFetch(fetchMock);
    render(<ConversationExperience relationshipId={relationshipId} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Retry original message' }));

    await waitFor(() => expect(apiCalls(requestMock)).toHaveLength(3));
    expect(apiCalls(requestMock)[1][0]).toContain('afterCursor=authoritative-cursor-0001');
    expect(JSON.parse(String(apiCalls(requestMock)[2][1]?.body))).toEqual({
      action: 'retry', messageId, idempotencyKey: 'original-idempotency-key',
    });
  });

  it('cancels an active execution and preserves the ordinary Emergency Stop boundary', async () => {
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline([])))
      .mockImplementationOnce(() => jsonResponse(timeline([])))
      .mockImplementationOnce(() => jsonResponse({
        schemaVersion: '1.0', outcome: 'ACCEPTED', message: message({ cards: [], partial: false }),
        executionId: '3ead2d21-f908-40b5-9510-b1e77f516d7e', authoritativeCursor: 'authoritative-cursor-0002', replayed: false,
      }))
      .mockImplementationOnce(() => jsonResponse({ schemaVersion: '1.0', state: 'CANCELLED', partial: true }))
      .mockImplementationOnce(() => jsonResponse(timeline([message({ processingState: 'CANCELLED', partial: true, completionReason: 'CANCELLED' })])));
    const requestMock = installFetch(fetchMock);
    render(<ConversationExperience relationshipId={relationshipId} />);

    fireEvent.change(await screen.findByLabelText('Message your professional'), { target: { value: 'Start work.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel response' }));

    await waitFor(() => expect(apiCalls(requestMock)).toHaveLength(5));
    expect(JSON.parse(String(apiCalls(requestMock)[3][1]?.body))).toEqual(expect.objectContaining({
      action: 'cancel', executionId: '3ead2d21-f908-40b5-9510-b1e77f516d7e',
    }));
    expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:cancel:3ead2d21-f908-40b5-9510-b1e77f516d7e`)).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Cancel response' })).toBeVisible();
    expect(requestMock.mock.calls.some(([url]) => String(url).includes('emergency-stop'))).toBe(false);
  });

  it('stops stream rendering on stop.applied and paginates older canonical messages', async () => {
    const older = message({ messageId: '341d3a3d-a1d9-4941-a64b-fe3c95513348', sequence: 1, cards: [], partial: false });
    const newer = message({ sequence: 2, cards: [], partial: false });
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline([newer], { nextCursor: 'older-page-cursor' })))
      .mockImplementationOnce(() => jsonResponse(timeline([older], { authoritativeCursor: 'authoritative-cursor-0001' })));
    const stream = controllableStream();
    const requestMock = installFetch(fetchMock, async (_input, init) => stream.response(init?.signal));
    render(<ConversationExperience relationshipId={relationshipId} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Load earlier messages' }));
    await waitFor(() => expect(apiCalls(requestMock)[1][0]).toContain('cursor=older-page-cursor'));
    await waitFor(() => expect(screen.getAllByText('Here is the current plan.')).toHaveLength(2));

    await act(async () => stream.push(streamEvent('stop.applied')));
    expect(await screen.findByText('stopped')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  });

  it('reports an initial timeline failure and settles the loading state', async () => {
    installFetch(() => jsonResponse({ title: 'Conversation is temporarily unavailable.' }, 503));
    render(<ConversationExperience relationshipId={relationshipId} />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Conversation is temporarily unavailable.');
    await waitFor(() => expect(screen.getByLabelText('Conversation timeline')).toHaveAttribute('aria-busy', 'false'));
    expect(screen.getByText('No messages yet. Start with a clear outcome for your professional.')).toBeVisible();
  });

  it('reconciles a saved outbox against a canonical message without resending it', async () => {
    const contribution = {
      clientMessageId: 'saved-client-message',
      idempotencyKey: 'saved-idempotency-key',
      text: 'Saved contribution',
    };
    localStorage.setItem(`waooaw:conversation:${relationshipId}:draft`, contribution.text);
    localStorage.setItem(`waooaw:conversation:${relationshipId}:outbox`, JSON.stringify(contribution));
    const canonical = message({ clientMessageId: contribution.clientMessageId, cards: [], partial: false });
    const fetchMock = jest.fn(() => jsonResponse(timeline([canonical])));
    const requestMock = installFetch(fetchMock);

    render(<ConversationExperience relationshipId={relationshipId} />);

    expect(await screen.findByText('Message reconciled with the authoritative timeline.')).toBeInTheDocument();
    expect(apiCalls(requestMock)).toHaveLength(1);
    expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:outbox`)).toBeNull();
    expect(screen.getByLabelText('Message your professional')).toHaveValue('');
  });

  it('submits a saved outbox after startup reconciliation and exposes a failed outcome', async () => {
    const contribution = {
      clientMessageId: 'saved-client-message',
      idempotencyKey: 'saved-idempotency-key',
      text: 'Saved contribution',
    };
    localStorage.setItem(`waooaw:conversation:${relationshipId}:outbox`, JSON.stringify(contribution));
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline([])))
      .mockImplementationOnce(() => jsonResponse({ title: 'Evidence could not be confirmed.' }, 503));
    installFetch(fetchMock);

    render(<ConversationExperience relationshipId={relationshipId} />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Evidence could not be confirmed.');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).not.toHaveTextContent('Sending'));
    expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:outbox`)).not.toBeNull();
  });

  it('advances read position when the timeline identifies an unread boundary', async () => {
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline([message()], { unreadBoundaryMessageId: messageId })))
      .mockImplementationOnce(() => jsonResponse({ schemaVersion: '1.0' }));
    const requestMock = installFetch(fetchMock);
    render(<ConversationExperience relationshipId={relationshipId} />);

    expect(await screen.findByText('Unread messages')).toBeVisible();
    await waitFor(() => expect(apiCalls(requestMock)).toHaveLength(2));
    expect(JSON.parse(String(apiCalls(requestMock)[1][1]?.body))).toEqual(expect.objectContaining({
      action: 'read',
      lastVisibleMessageId: messageId,
      authoritativeCursor: 'authoritative-cursor-0001',
    }));
  });

  it('parses typed heartbeat and delta events while preserving Last-Event-ID', async () => {
    localStorage.setItem(`waooaw:conversation:${relationshipId}:stream-cursor`, 'event-before-reload');
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline()))
      .mockImplementationOnce(() => jsonResponse(timeline()));
    const requestMock = installFetch(fetchMock, async (_input, init) => streamResponse(init?.signal, [
      streamEvent('heartbeat', { eventId: 'heartbeat-1' }),
      streamEvent('response.delta', { eventId: 'delta-2', executionId: 'active-execution', data: { contentIndex: 0, appendText: 'Draft text', partial: true } }),
    ]));
    render(<ConversationExperience relationshipId={relationshipId} />);
    expect(await screen.findByText('Professional response updating: Draft text')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel response' })).toBeVisible();
    expect((streamCalls(requestMock)[0][1]?.headers as Headers).get('Last-Event-ID')).toBe('event-before-reload');
    expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:stream-cursor`)).toBe('delta-2');
    await act(async () => window.dispatchEvent(new Event('offline')));
    expect(screen.getByText('offline')).toBeVisible();
  });

  it('reconciles once on 410, clears the expired cursor, and does not loop', async () => {
    localStorage.setItem(`waooaw:conversation:${relationshipId}:stream-cursor`, 'expired-event');
    const fetchMock = jest.fn(() => jsonResponse(timeline()));
    let streamAttempt = 0;
    const requestMock = installFetch(fetchMock, async (_input, init) => {
      streamAttempt += 1;
      return streamAttempt === 1 ? statusResponse(410) : streamResponse(init?.signal);
    });
    render(<ConversationExperience relationshipId={relationshipId} />);

    await waitFor(() => expect(streamCalls(requestMock)).toHaveLength(2));
    expect(apiCalls(requestMock)).toHaveLength(2);
    expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:stream-cursor`)).toBeNull();
    await act(async () => Promise.resolve());
    expect(streamCalls(requestMock)).toHaveLength(2);
  });

  it('restores stopped state on 423 without retrying the stream', async () => {
    const requestMock = installFetch(
      () => jsonResponse(timeline()),
      async () => statusResponse(423),
    );
    render(<ConversationExperience relationshipId={relationshipId} />);

    expect(await screen.findByText('stopped')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
    await act(async () => Promise.resolve());
    expect(streamCalls(requestMock)).toHaveLength(1);
  });

  it('invokes an approved retry operation for an enabled typed-card command', async () => {
    const retryCard = {
      ...governedCards[1],
      commands: [{ commandId: 'RETRY_MESSAGE', label: 'Retry governed work', availability: 'AVAILABLE' as const }],
    };
    const unresolved = message({ deliveryState: 'UNRESOLVED', processingState: 'FAILED', cards: [retryCard], partial: false });
    localStorage.setItem(`waooaw:conversation:${relationshipId}:retry:${messageId}`, 'original-idempotency-key');
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline([unresolved])))
      .mockImplementationOnce(() => jsonResponse(timeline([unresolved])))
      .mockImplementationOnce(() => jsonResponse({ schemaVersion: '1.0', outcome: 'REPLAYED', message: unresolved, authoritativeCursor: 'cursor', replayed: true }));
    const requestMock = installFetch(fetchMock);
    render(<ConversationExperience relationshipId={relationshipId} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Retry governed work' }));
    await waitFor(() => expect(apiCalls(requestMock)).toHaveLength(3));
    expect(JSON.parse(String(apiCalls(requestMock)[2][1]?.body))).toEqual({
      action: 'retry', messageId, idempotencyKey: 'original-idempotency-key',
    });
  });

  it('restores active execution after reload and clears cancellation only on a terminal event', async () => {
    const stream = controllableStream();
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline([message({ processingState: 'RUNNING', cards: [] })])))
      .mockImplementationOnce(() => jsonResponse(timeline([message({ processingState: 'RUNNING', cards: [] })])))
      .mockImplementationOnce(() => jsonResponse({ schemaVersion: '1.0', state: 'CANCELLED', partial: true }))
      .mockImplementationOnce(() => jsonResponse(timeline([message({ processingState: 'RUNNING', cards: [] })])));
    installFetch(fetchMock, async (_input, init) => stream.response(init?.signal));
    render(<ConversationExperience relationshipId={relationshipId} />);

    await screen.findByText('Here is the current plan.');
    await act(async () => stream.push(streamEvent('processing.started', { executionId: 'reloaded-execution' })));
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel response' }));
    await waitFor(() => expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:cancel:reloaded-execution`)).not.toBeNull());
    expect(screen.getByRole('button', { name: 'Cancel response' })).toBeVisible();

    await act(async () => stream.push(streamEvent('stream.cancelled', { eventId: 'terminal-event', executionId: 'reloaded-execution' })));
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Cancel response' })).not.toBeInTheDocument());
    expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:cancel:reloaded-execution`)).toBeNull();
  });

  it('rejects retry without its original identity and preserves cancellation identity after failure', async () => {
    const unresolved = message({ deliveryState: 'FAILED', processingState: 'FAILED', evidenceState: 'FAILED', cards: [], partial: false });
    const fetchMock = jest.fn()
      .mockImplementationOnce(() => jsonResponse(timeline([unresolved])))
      .mockImplementationOnce(() => jsonResponse(timeline([])))
      .mockImplementationOnce(() => jsonResponse({
        schemaVersion: '1.0', outcome: 'ACCEPTED', message: message({ cards: [], partial: false }),
        executionId: '3ead2d21-f908-40b5-9510-b1e77f516d7e', authoritativeCursor: 'authoritative-cursor-0002', replayed: false,
      }))
      .mockImplementationOnce(() => jsonResponse({}, 503));
    installFetch(fetchMock);
    render(<ConversationExperience relationshipId={relationshipId} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Retry original message' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Retry identity is unavailable on this device.');

    fireEvent.change(screen.getByLabelText('Message your professional'), { target: { value: 'Start cancellable work.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel response' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The conversation outcome is unknown.');
    expect(localStorage.getItem(`waooaw:conversation:${relationshipId}:cancel:3ead2d21-f908-40b5-9510-b1e77f516d7e`)).not.toBeNull();
  });
});