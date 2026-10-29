jest.mock('next/server', () => {
  class MockNextResponse {
    readonly status: number;
    readonly body: unknown;
    readonly headers: Record<string, string>;

    constructor(body: unknown, init?: { status?: number; headers?: Record<string, string> }) {
      this.status = init?.status ?? 200;
      this.body = body;
      this.headers = init?.headers ?? {};
    }

    async json() {
      return this.body;
    }

    static json(body: unknown, init?: { status?: number; headers?: Record<string, string> }) {
      return new MockNextResponse(body, init);
    }
  }

  return { NextResponse: MockNextResponse };
});

jest.mock('@/lib/web-session-store', () => ({
  oidcTransactionStoreReady: jest.fn(),
  sessionStoreReady: jest.fn(),
}));
jest.mock('@/lib/auth-abuse-limiter', () => ({
  authAbuseLimiterStatus: jest.fn(),
}));

import { GET } from '@/app/api/health/ready/route';
import { authAbuseLimiterStatus } from '@/lib/auth-abuse-limiter';
import { oidcTransactionStoreReady, sessionStoreReady } from '@/lib/web-session-store';

const mockedOidcTransactionStoreReady = jest.mocked(oidcTransactionStoreReady);
const mockedSessionStoreReady = jest.mocked(sessionStoreReady);
const mockedAuthAbuseLimiterStatus = jest.mocked(authAbuseLimiterStatus);
const originalEnvironment = { ...process.env };

describe('revision readiness', () => {
  beforeEach(() => {
    process.env = {
      ...originalEnvironment,
      BUSINESS_PLATFORM_URL: 'https://api.example',
      KEYCLOAK_ISSUER: 'https://identity.example/realms/waooaw',
      KEYCLOAK_READINESS_ISSUER: 'https://identity-internal.example/realms/waooaw',
      NODE_ENV: 'production',
    };
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    Object.defineProperty(AbortSignal, 'timeout', {
      configurable: true,
      value: jest.fn(() => new AbortController().signal),
    });
    mockedSessionStoreReady.mockReset();
    mockedOidcTransactionStoreReady.mockReset().mockResolvedValue(true);
    mockedAuthAbuseLimiterStatus.mockReset().mockResolvedValue({ ready: true, reason: 'READY' });
  });

  afterAll(() => {
    process.env = originalEnvironment;
  });

  it('requires only OIDC transaction persistence in disabled session mode', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'disabled';

    const response = await GET();

    expect(response.status).toBe(204);
    expect(mockedAuthAbuseLimiterStatus).toHaveBeenCalledTimes(1);
    expect(mockedOidcTransactionStoreReady).toHaveBeenCalledTimes(1);
    expect(mockedSessionStoreReady).not.toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      'https://identity-internal.example/realms/waooaw/.well-known/openid-configuration',
      expect.objectContaining({ cache: 'no-store' })
    );
  });

  it('fails closed when the authentication limiter is unavailable in disabled session mode', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'disabled';
    mockedAuthAbuseLimiterStatus.mockResolvedValue({ ready: false, reason: 'LIMITER_UNAVAILABLE' });

    const response = await GET();

    expect(response.status).toBe(503);
    expect(mockedSessionStoreReady).not.toHaveBeenCalled();
  });

  it('reports the restart hold without exposing credentials or bypassing readiness', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'disabled';
    mockedAuthAbuseLimiterStatus.mockResolvedValue({
      ready: false,
      reason: 'RESTART_HOLD',
      retryAfterSeconds: 73,
    });

    const response = await GET();

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      code: 'REVISION_NOT_READY',
      dependencies: {
        identity: true,
        membership: true,
        transactionStore: true,
        sessionStore: true,
        limiter: { ready: false, reason: 'RESTART_HOLD', retryAfterSeconds: 73 },
      },
    });
    expect(response.headers).toEqual({ 'Cache-Control': 'no-store', 'Retry-After': '73' });
  });

  it('fails closed when OIDC transaction persistence is unavailable in disabled session mode', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'disabled';
    mockedOidcTransactionStoreReady.mockResolvedValue(false);

    const response = await GET();

    expect(response.status).toBe(503);
    expect(mockedSessionStoreReady).not.toHaveBeenCalled();
  });

  it('fails closed when an enabled session mode lacks accepted digests', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'enforced';

    const response = await GET();

    expect(response.status).toBe(503);
    expect(mockedSessionStoreReady).not.toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('requires the session store when session authority is enabled', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'shadow';
    process.env.WEB_SESSION_CONFIG_DIGEST = `sha256:${'a'.repeat(64)}`;
    process.env.WEB_SESSION_EXPECTED_CONFIG_DIGEST = process.env.WEB_SESSION_CONFIG_DIGEST;
    process.env.WEB_SESSION_TELEMETRY_ROUTE_DIGEST = `sha256:${'b'.repeat(64)}`;
    process.env.WEB_SESSION_EXPECTED_TELEMETRY_ROUTE_DIGEST = process.env.WEB_SESSION_TELEMETRY_ROUTE_DIGEST;
    mockedSessionStoreReady.mockResolvedValue(true);

    const response = await GET();

    expect(response.status).toBe(204);
    expect(mockedSessionStoreReady).toHaveBeenCalledTimes(1);
  });
});
