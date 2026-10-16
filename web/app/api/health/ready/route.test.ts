/** @jest-environment node */

import { authAbuseLimiterReady } from '@/lib/auth-abuse-limiter';
import { sessionStoreReady } from '@/lib/web-session-store';
import { GET } from './route';

jest.mock('@/lib/auth-abuse-limiter', () => ({ authAbuseLimiterReady: jest.fn() }));
jest.mock('@/lib/web-session-store', () => ({ sessionStoreReady: jest.fn() }));

const readinessEnvironment = {
  KEYCLOAK_ISSUER: 'https://identity.example/realms/waooaw',
  BUSINESS_PLATFORM_URL: 'https://business.example',
  WEB_SESSION_CONFIG_DIGEST: 'config-digest',
  WEB_SESSION_EXPECTED_CONFIG_DIGEST: 'config-digest',
  WEB_SESSION_TELEMETRY_ROUTE_DIGEST: 'telemetry-digest',
  WEB_SESSION_EXPECTED_TELEMETRY_ROUTE_DIGEST: 'telemetry-digest',
};

beforeEach(() => {
  Object.assign(process.env, readinessEnvironment);
  jest.mocked(authAbuseLimiterReady).mockReset().mockResolvedValue(true);
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
});

it('fails closed without exposing dependency detail', async () => {
  process.env.WEB_SESSION_CONFIG_DIGEST = 'unexpected';
  const response = await GET();
  expect(response.status).toBe(503);
  await expect(response.json()).resolves.toEqual({ code: 'REVISION_NOT_READY' });
  expect(fetch).not.toHaveBeenCalled();
});
