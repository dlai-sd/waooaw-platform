/** @jest-environment node */

import { redisCommand } from '@/lib/redis-command';
import { authAbuseLimiterStatus, checkAuthAbuse } from '@/lib/auth-abuse-limiter';
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
    process.env.AUTH_ABUSE_DIGEST_KEY = Buffer.alloc(32, 10).toString('base64');
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

  integrationTest('recovers Demo at 120 seconds while preserving hourly limits and non-Demo holds', async () => {
    process.env.REDIS_URL = process.env.REDIS_INTEGRATION_URL;
    process.env.WAOOAW_ENVIRONMENT = 'demo';
    process.env.AUTH_ABUSE_DIGEST_KEY = Buffer.alloc(32, 10).toString('base64');
    process.env.AUTH_ABUSE_LIMITS_JSON = JSON.stringify(
      Object.fromEntries(
        ['AUTH_START', 'AUTH_CALLBACK', 'RECOVERY', 'PROVIDER_LINK', 'PROVIDER_UNLINK', 'RESEND', 'CREDENTIAL'].map(
          (action) => [action, { limit: 1, windowSeconds: 3600 }]
        )
      )
    );
    const request = new NextRequest('https://app.example/api/auth/recovery', {
      headers: { 'x-forwarded-for': '203.0.113.11' },
    });
    const epochKey = 'waooaw:demo:auth-abuse:v1:epoch';
    const requestCounter = () => checkAuthAbuse(request, 'RECOVERY');
    const setElapsed = async (seconds: number) => {
      await redisCommand([
        'EVAL',
        "local t=redis.call('TIME');return redis.call('SET',KEYS[1],tonumber(t[1])*1000+math.floor(tonumber(t[2])/1000)-tonumber(ARGV[1]))",
        '1',
        epochKey,
        String(seconds * 1000),
      ]);
    };

    await redisCommand(['DEL', epochKey]);
    await expect(authAbuseLimiterStatus()).resolves.toEqual({
      ready: false,
      reason: 'RESTART_HOLD',
      retryAfterSeconds: 120,
    });
    await setElapsed(119);
    await expect(authAbuseLimiterStatus()).resolves.toMatchObject({ ready: false, reason: 'RESTART_HOLD' });
    await expect(requestCounter()).resolves.toMatchObject({ allowed: false, reason: 'RESTART_HOLD' });
    await setElapsed(120);
    await expect(authAbuseLimiterStatus()).resolves.toEqual({ ready: true, reason: 'READY' });
    await expect(requestCounter()).resolves.toMatchObject({ allowed: true });
    await expect(requestCounter()).resolves.toMatchObject({
      allowed: false,
      reason: 'QUOTA_EXCEEDED',
      retryAfterSeconds: expect.any(Number),
    });
    const timeToReset = (await requestCounter()).retryAfterSeconds;
    expect(timeToReset).toBeGreaterThan(3500);
    await redisCommand(['DEL', epochKey]);
    await expect(requestCounter()).resolves.toMatchObject({ allowed: false, reason: 'RESTART_HOLD' });

    for (const environment of ['uat', 'prod']) {
      process.env.WAOOAW_ENVIRONMENT = environment;
      await redisCommand(['SET', `waooaw:${environment}:auth-abuse:v1:epoch`, String(Date.now() - 120_000)]);
      await expect(authAbuseLimiterStatus()).resolves.toMatchObject({
        ready: false,
        reason: 'RESTART_HOLD',
        retryAfterSeconds: expect.any(Number),
      });
    }
  });
});
