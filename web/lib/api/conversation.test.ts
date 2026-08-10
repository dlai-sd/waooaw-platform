/** @jest-environment node */

jest.mock('server-only', () => ({}));

describe('conversation Business Platform adapter', () => {
  beforeEach(() => jest.clearAllMocks());

  it('forwards only server bearer and resume headers to the BP stream', async () => {
    const fetchMock = jest.fn().mockResolvedValue(new Response('event: heartbeat\ndata: {}\n\n'));
    global.fetch = fetchMock;
    const { openConversationStream } = await import('./conversation');
    const signal = new AbortController().signal;

    await openConversationStream('relationship/id', 'private-token', 'event-42', signal);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://localhost:5001/api/v1/employment/relationships/relationship%2Fid/conversation/stream');
    const headers = init.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer private-token');
    expect(headers.get('Last-Event-ID')).toBe('event-42');
    expect(headers.get('Accept')).toBe('text/event-stream');
    expect(init.cache).toBe('no-store');
    expect(init.signal).toBe(signal);
  });
});