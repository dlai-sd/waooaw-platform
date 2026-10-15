jest.mock('next/server', () => {
  class MockNextResponse {
    readonly status: number;

    constructor(_body: unknown, init?: { status?: number }) {
      this.status = init?.status ?? 200;
    }

    static json(_body: unknown, init?: { status?: number }) {
      return new MockNextResponse(null, init);
    }
  }

  return { NextResponse: MockNextResponse };
});

jest.mock('@/lib/web-session-store', () => ({
  sessionStoreReady: jest.fn(),
}));

import { GET } from '@/app/api/health/ready/route';
import { sessionStoreReady } from '@/lib/web-session-store';

const mockedSessionStoreReady = jest.mocked(sessionStoreReady);
const originalEnvironment = { ...process.env };

describe('revision readiness', () => {
  beforeEach(() => {
    process.env = {
      ...originalEnvironment,
      BUSINESS_PLATFORM_URL: 'https://api.example',
      KEYCLOAK_ISSUER: 'https://identity.example/realms/waooaw',
      NODE_ENV: 'production',
    };
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    Object.defineProperty(AbortSignal, 'timeout', {
      configurable: true,
      value: jest.fn(() => new AbortController().signal),
    });
    mockedSessionStoreReady.mockReset();
  });

  afterAll(() => {
    process.env = originalEnvironment;
  });

  it('does not require inactive session dependencies in disabled mode', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'disabled';

    const response = await GET();

    expect(response.status).toBe(204);
    expect(mockedSessionStoreReady).not.toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledTimes(2);
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
