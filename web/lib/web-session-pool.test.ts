/** @jest-environment node */

const mockResolvers: Array<(value: Array<{ ready: boolean }>) => void> = [];
const mockSql = jest.fn(
  () =>
    new Promise<Array<{ ready: boolean }>>((resolve) => {
      mockResolvers.push(resolve);
    })
);

jest.mock('postgres', () => ({
  __esModule: true,
  default: jest.fn(() => mockSql),
}));

import { sessionStoreReady } from '@/lib/web-session-store';

describe('Web session database pool', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockResolvers.length = 0;
    mockSql.mockClear();
    const key = Buffer.alloc(32, 4).toString('base64');
    process.env.WEB_SESSION_DATABASE_URL = 'postgresql://web_session_app:test@postgres/waooaw';
    process.env.SESSION_HANDLE_DIGEST_KEYS = JSON.stringify({ v1: key });
    process.env.SESSION_PROTOCOL_DIGEST_KEYS = JSON.stringify({ v1: key });
    process.env.SESSION_TOKEN_ENVELOPE_KEYS = JSON.stringify({ v1: key });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('bounds concurrency at five and rejects excess acquisition after one second', async () => {
    const active = Array.from({ length: 5 }, () => sessionStoreReady());
    const saturated = sessionStoreReady();
    const saturatedExpectation = expect(saturated).rejects.toThrow('Web session database pool acquisition timed out');

    await Promise.resolve();
    expect(mockSql).toHaveBeenCalledTimes(5);
    await jest.advanceTimersByTimeAsync(1_000);
    await saturatedExpectation;

    for (const resolve of mockResolvers) resolve([{ ready: true }]);
    await expect(Promise.all(active)).resolves.toEqual([true, true, true, true, true]);
  });
});
