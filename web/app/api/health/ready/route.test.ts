/** @jest-environment node */

import { authAbuseLimiterStatus } from '@/lib/auth-abuse-limiter';
import { oidcTransactionStoreReady, sessionStoreReady } from '@/lib/web-session-store';
import { GET } from './route';

jest.mock('@/lib/auth-abuse-limiter', () => ({ authAbuseLimiterStatus: jest.fn() }));
jest.mock('@/lib/web-session-store', () => ({
  oidcTransactionStoreReady: jest.fn(),
  sessionStoreReady: jest.fn(),
}));

const readinessEnvironment = {
  KEYCLOAK_ISSUER: 'https://identity.example/realms/waooaw',
  KEYCLOAK_READINESS_ISSUER: 'https://identity-internal.example/realms/waooaw',
  BUSINESS_PLATFORM_URL: 'https://business.example',
  WEB_SESSION_CONFIG_DIGEST: 'config-digest',
  WEB_SESSION_EXPECTED_CONFIG_DIGEST: 'config-digest',
  WEB_SESSION_TELEMETRY_ROUTE_DIGEST: 'telemetry-digest',
  WEB_SESSION_EXPECTED_TELEMETRY_ROUTE_DIGEST: 'telemetry-digest',
};

beforeEach(() => {
  Object.assign(process.env, readinessEnvironment);
  jest.mocked(authAbuseLimiterStatus).mockReset().mockResolvedValue({ ready: true, reason: 'READY' });
  jest.mocked(oidcTransactionStoreReady).mockReset().mockResolvedValue(true);
  jest.mocked(sessionStoreReady).mockReset().mockResolvedValue(true);
  jest.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }));
});

afterEach(() => {
  jest.restoreAllMocks();
  for (const key of Object.keys(readinessEnvironment)) delete process.env[key];
});

it('reports ready only when configuration, schema, grants, and dependencies pass', async () => {
  const response = await GET();
  expect(response.status).toBe(204);
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch).toHaveBeenNthCalledWith(
    1,
    'https://identity-internal.example/realms/waooaw/.well-known/openid-configuration',
    expect.objectContaining({ cache: 'no-store' })
  );
  expect(oidcTransactionStoreReady).not.toHaveBeenCalled();
  expect(sessionStoreReady).toHaveBeenCalledTimes(1);
});

it('fails closed without the internal identity readiness issuer', async () => {
  process.env.KEYCLOAK_READINESS_ISSUER = '';
  const response = await GET();
  expect(response.status).toBe(503);
  expect(fetch).not.toHaveBeenCalled();
});

it('fails closed without exposing dependency detail', async () => {
  process.env.WEB_SESSION_CONFIG_DIGEST = 'unexpected';
  const response = await GET();
  expect(response.status).toBe(503);
  await expect(response.json()).resolves.toEqual({
    code: 'REVISION_NOT_READY',
    correlationId: response.headers.get('x-correlation-id'),
  });
  expect(fetch).not.toHaveBeenCalled();
});

it('reports the restart hold without making the revision ready', async () => {
  jest.mocked(authAbuseLimiterStatus).mockResolvedValue({
    ready: false,
    reason: 'RESTART_HOLD',
    retryAfterSeconds: 120,
  });
  const response = await GET();
  expect(response.status).toBe(503);
  expect(response.headers.get('Retry-After')).toBe('120');
  expect(response.headers.get('Cache-Control')).toBe('no-store');
  await expect(response.json()).resolves.toMatchObject({
    code: 'REVISION_NOT_READY',
    dependencies: { limiter: { ready: false, reason: 'RESTART_HOLD', retryAfterSeconds: 120 } },
  });
});

it('fails closed without a recovery promise when Redis is unavailable', async () => {
  jest.mocked(authAbuseLimiterStatus).mockResolvedValue({
    ready: false,
    reason: 'LIMITER_UNAVAILABLE',
  });
  const response = await GET();
  expect(response.status).toBe(503);
  expect(response.headers.has('Retry-After')).toBe(false);
  await expect(response.json()).resolves.toMatchObject({
    dependencies: { limiter: { ready: false, reason: 'LIMITER_UNAVAILABLE' } },
  });
});
