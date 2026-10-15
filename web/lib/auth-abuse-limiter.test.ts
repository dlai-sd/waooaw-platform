/** @jest-environment node */

import { NextRequest } from 'next/server';
import { checkAuthAbuse } from '@/lib/auth-abuse-limiter';
import { redisCommand } from '@/lib/redis-command';

jest.mock('@/lib/redis-command', () => ({ redisCommand: jest.fn() }));

const key = Buffer.alloc(32, 7).toString('base64');
const limits = {
  AUTH_START: { limit: 20, windowSeconds: 600 },
  AUTH_CALLBACK: { limit: 30, windowSeconds: 600 },
  RECOVERY: { limit: 5, windowSeconds: 3600 },
  PROVIDER_LINK: { limit: 10, windowSeconds: 3600 },
  PROVIDER_UNLINK: { limit: 10, windowSeconds: 3600 },
  RESEND: { limit: 5, windowSeconds: 900 },
  CREDENTIAL: { limit: 10, windowSeconds: 3600 },
};

describe('authentication abuse limiter', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.REDIS_URL = 'redis://redis:6379/0';
    process.env.WAOOAW_ENVIRONMENT = 'demo';
    process.env.AUTH_ABUSE_LIMITS_JSON = JSON.stringify(limits);
    process.env.SESSION_PROTOCOL_DIGEST_KEYS = JSON.stringify({ v1: key });
    process.env.SESSION_PROTOCOL_DIGEST_WRITE_VERSION = 'v1';
  });

  it('uses only an environment-scoped keyed digest with a bounded TTL', async () => {
    jest.mocked(redisCommand).mockResolvedValue([1, 599_000]);
    const request = new NextRequest('https://app.example/api/auth/signin/keycloak-google', {
      headers: { 'x-forwarded-for': '203.0.113.42' },
    });

    await expect(checkAuthAbuse(request, 'AUTH_START')).resolves.toEqual({
      allowed: true,
      reason: 'ALLOWED',
    });

    const command = jest.mocked(redisCommand).mock.calls[0][0];
    expect(command[0]).toBe('EVAL');
    expect(command.join(' ')).not.toContain('203.0.113.42');
    expect(command[4]).toMatch(/^waooaw:demo:auth-abuse:v1:auth_start:[0-9a-f]{64}$/);
    expect(command.at(-2)).toBe('600000');
    expect(command.at(-1)).toBe('20');
  });

  it('fails closed for the longest quota window after a restart', async () => {
    jest.mocked(redisCommand).mockResolvedValue([-2, 3_600_000]);

    await expect(
      checkAuthAbuse(new NextRequest('https://app.example/api/auth/callback/keycloak-google'), 'AUTH_CALLBACK')
    ).resolves.toEqual({
      allowed: false,
      reason: 'RESTART_HOLD',
      retryAfterSeconds: 3600,
    });
  });

  it('fails closed when Redis is unavailable', async () => {
    jest.mocked(redisCommand).mockRejectedValue(new Error('unavailable'));

    await expect(
      checkAuthAbuse(new NextRequest('https://app.example/api/auth/signin/keycloak-google'), 'AUTH_START')
    ).resolves.toEqual({
      allowed: false,
      reason: 'LIMITER_UNAVAILABLE',
    });
  });
});
