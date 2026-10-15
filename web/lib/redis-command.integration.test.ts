/** @jest-environment node */

import { redisCommand } from '@/lib/redis-command';
import { checkAuthAbuse } from '@/lib/auth-abuse-limiter';
import { NextRequest } from 'next/server';

const integrationTest = process.env.REDIS_INTEGRATION_URL ? it : it.skip;

describe('Redis command transport', () => {
  integrationTest('executes the atomic limiter response over the Redis wire protocol', async () => {
    process.env.REDIS_URL = process.env.REDIS_INTEGRATION_URL;

    await expect(redisCommand(['SET', 'wc123:transport', 'ready', 'EX', '10'])).resolves.toBe('OK');
    await expect(redisCommand(['GET', 'wc123:transport'])).resolves.toBe('ready');
    await expect(
      redisCommand(['EVAL', "return {1, redis.call('PTTL', KEYS[1])}", '1', 'wc123:transport'])
    ).resolves.toEqual([1, expect.any(Number)]);
  });

  integrationTest('holds after an epoch reset and then enforces the atomic quota', async () => {
    process.env.REDIS_URL = process.env.REDIS_INTEGRATION_URL;
    process.env.WAOOAW_ENVIRONMENT = 'wc123-integration';
    process.env.SESSION_PROTOCOL_DIGEST_KEYS = JSON.stringify({
      v1: Buffer.alloc(32, 9).toString('base64'),
    });
    process.env.SESSION_PROTOCOL_DIGEST_WRITE_VERSION = 'v1';
    process.env.AUTH_ABUSE_LIMITS_JSON = JSON.stringify({
      AUTH_START: { limit: 1, windowSeconds: 10 },
      AUTH_CALLBACK: { limit: 1, windowSeconds: 10 },
      RECOVERY: { limit: 1, windowSeconds: 10 },
      PROVIDER_LINK: { limit: 1, windowSeconds: 10 },
      PROVIDER_UNLINK: { limit: 1, windowSeconds: 10 },
      RESEND: { limit: 1, windowSeconds: 10 },
      CREDENTIAL: { limit: 1, windowSeconds: 10 },
    });
    const request = new NextRequest('https://app.example/api/auth/signin/keycloak-google', {
      headers: { 'x-forwarded-for': '203.0.113.10' },
    });

    await expect(checkAuthAbuse(request, 'AUTH_START')).resolves.toEqual(
      expect.objectContaining({ allowed: false, reason: 'RESTART_HOLD' })
    );
    await redisCommand(['SET', 'waooaw:wc123-integration:auth-abuse:v1:epoch', '0']);
    await expect(checkAuthAbuse(request, 'AUTH_START')).resolves.toEqual({
      allowed: true,
      reason: 'ALLOWED',
    });
    await expect(checkAuthAbuse(request, 'AUTH_START')).resolves.toEqual(
      expect.objectContaining({ allowed: false, reason: 'QUOTA_EXCEEDED' })
    );
  });
});
