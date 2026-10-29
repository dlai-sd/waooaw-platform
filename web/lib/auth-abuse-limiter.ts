import 'server-only';

import { createHmac } from 'node:crypto';
import { redisCommand } from '@/lib/redis-command';
import { logServerFailure } from '@/lib/server-diagnostics';
import { type NextRequest, NextResponse } from 'next/server';

export type AuthAbuseAction =
  | 'AUTH_START'
  | 'AUTH_CALLBACK'
  | 'RECOVERY'
  | 'PROVIDER_LINK'
  | 'PROVIDER_UNLINK'
  | 'RESEND'
  | 'CREDENTIAL';

interface Limit {
  limit: number;
  windowSeconds: number;
}

type LimitCatalog = Record<AuthAbuseAction, Limit>;

export interface AuthAbuseDecision {
  allowed: boolean;
  reason: 'ALLOWED' | 'QUOTA_EXCEEDED' | 'RESTART_HOLD' | 'LIMITER_UNAVAILABLE';
  retryAfterSeconds?: number;
}

export interface AuthAbuseReadiness {
  ready: boolean;
  reason: 'READY' | 'RESTART_HOLD' | 'LIMITER_UNAVAILABLE';
  retryAfterSeconds?: number;
}

const script = `
local now = redis.call('TIME')
local now_ms = (tonumber(now[1]) * 1000) + math.floor(tonumber(now[2]) / 1000)
local epoch = redis.call('GET', KEYS[1])
if not epoch then
  redis.call('SET', KEYS[1], now_ms, 'NX')
  return {-2, tonumber(ARGV[1])}
end
local elapsed = now_ms - tonumber(epoch)
if elapsed < tonumber(ARGV[1]) then
  return {-2, tonumber(ARGV[1]) - elapsed}
end
local count = redis.call('INCR', KEYS[2])
if count == 1 then redis.call('PEXPIRE', KEYS[2], ARGV[2]) end
local ttl = redis.call('PTTL', KEYS[2])
if count > tonumber(ARGV[3]) then return {0, ttl} end
return {1, ttl}
`;

const readinessScript = `
local now = redis.call('TIME')
local now_ms = (tonumber(now[1]) * 1000) + math.floor(tonumber(now[2]) / 1000)
local epoch = redis.call('GET', KEYS[1])
if not epoch then
  redis.call('SET', KEYS[1], now_ms, 'NX')
  return {-2, tonumber(ARGV[1])}
end
local elapsed = now_ms - tonumber(epoch)
if elapsed < tonumber(ARGV[1]) then
  return {-2, tonumber(ARGV[1]) - elapsed}
end
return {1, 0}
`;

function catalog(): LimitCatalog {
  const raw = process.env.AUTH_ABUSE_LIMITS_JSON;
  if (!raw) throw new Error('AUTH_ABUSE_LIMITS_JSON is required');
  const parsed = JSON.parse(raw) as Partial<Record<AuthAbuseAction, Partial<Limit>>>;
  const actions: AuthAbuseAction[] = [
    'AUTH_START',
    'AUTH_CALLBACK',
    'RECOVERY',
    'PROVIDER_LINK',
    'PROVIDER_UNLINK',
    'RESEND',
    'CREDENTIAL',
  ];
  return Object.fromEntries(
    actions.map((action) => {
      const value = parsed[action];
      if (
        !value ||
        typeof value.limit !== 'number' ||
        !Number.isInteger(value.limit) ||
        value.limit < 1 ||
        typeof value.windowSeconds !== 'number' ||
        !Number.isInteger(value.windowSeconds) ||
        value.windowSeconds < 1
      )
        throw new Error(`AUTH_ABUSE_LIMITS_JSON.${action} is invalid`);
      return [action, { limit: value.limit, windowSeconds: value.windowSeconds }];
    })
  ) as LimitCatalog;
}

function digestKey(): Buffer {
  const raw = process.env.AUTH_ABUSE_DIGEST_KEY;
  if (!raw) throw new Error('Authentication abuse digest key is required');
  const key = Buffer.from(raw, 'utf8');
  if (key.length < 32) throw new Error('Authentication abuse digest key is invalid');
  return key;
}

function environmentName(): string {
  const environment = process.env.WAOOAW_ENVIRONMENT?.trim().toLowerCase();
  if (!environment || !/^[a-z0-9-]{1,32}$/.test(environment)) throw new Error('WAOOAW_ENVIRONMENT is required');
  return environment;
}

function restartHoldMs(environment: string, limits: LimitCatalog): number {
  // Temporary Founder-approved Demo exception: counter loss can replenish hourly quotas.
  return environment === 'demo'
    ? 120_000
    : Math.max(...Object.values(limits).map((value) => value.windowSeconds)) * 1000;
}

function requestSubject(request: NextRequest, action: AuthAbuseAction): string {
  const address =
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-real-ip')?.trim() ||
    'unavailable';
  return `${action}\0${address}\0${request.nextUrl.pathname}`;
}

export async function checkAuthAbuse(request: NextRequest, action: AuthAbuseAction): Promise<AuthAbuseDecision> {
  try {
    const limits = catalog();
    const selected = limits[action];
    const environment = environmentName();
    const subject = createHmac('sha256', digestKey())
      .update(`auth-abuse-v1\0${environment}\0${requestSubject(request, action)}`)
      .digest('hex');
    const prefix = `waooaw:${environment}:auth-abuse:v1`;
    const response = await redisCommand([
      'EVAL',
      script,
      '2',
      `${prefix}:epoch`,
      `${prefix}:${action.toLowerCase()}:${subject}`,
      String(restartHoldMs(environment, limits)),
      String(selected.windowSeconds * 1000),
      String(selected.limit),
    ]);
    if (!Array.isArray(response) || typeof response[0] !== 'number' || typeof response[1] !== 'number')
      throw new Error('Redis limiter response is invalid');
    const retryAfterSeconds = Math.max(1, Math.ceil(response[1] / 1000));
    if (response[0] === 1) return { allowed: true, reason: 'ALLOWED' };
    if (response[0] === -2) return { allowed: false, reason: 'RESTART_HOLD', retryAfterSeconds };
    return { allowed: false, reason: 'QUOTA_EXCEEDED', retryAfterSeconds };
  } catch (error) {
    logServerFailure('identity.abuse_limiter.failed', error, { action });
    return { allowed: false, reason: 'LIMITER_UNAVAILABLE' };
  }
}

export async function authAbuseLimiterStatus(): Promise<AuthAbuseReadiness> {
  try {
    const limits = catalog();
    digestKey();
    const environment = environmentName();
    const response = await redisCommand([
      'EVAL',
      readinessScript,
      '1',
      `waooaw:${environment}:auth-abuse:v1:epoch`,
      String(restartHoldMs(environment, limits)),
    ]);
    if (!Array.isArray(response) || typeof response[1] !== 'number' || !Number.isFinite(response[1]))
      throw new Error('Redis limiter readiness response is invalid');
    if (response[0] === 1 && response[1] === 0) return { ready: true, reason: 'READY' };
    if (response[0] === -2 && response[1] > 0) {
      return { ready: false, reason: 'RESTART_HOLD', retryAfterSeconds: Math.ceil(response[1] / 1000) };
    }
    throw new Error('Redis limiter readiness response is invalid');
  } catch (error) {
    logServerFailure('identity.abuse_limiter.readiness_failed', error, {}, 'warn');
    return { ready: false, reason: 'LIMITER_UNAVAILABLE' };
  }
}

export async function authAbuseLimiterReady(): Promise<boolean> {
  return (await authAbuseLimiterStatus()).ready;
}

export async function enforceAuthAbuse(request: NextRequest, action: AuthAbuseAction): Promise<NextResponse | null> {
  const decision = await checkAuthAbuse(request, action);
  if (decision.allowed) return null;
  const unavailable = decision.reason === 'LIMITER_UNAVAILABLE' || decision.reason === 'RESTART_HOLD';
  return NextResponse.json(
    {
      code: unavailable ? 'ABUSE_LIMITER_UNAVAILABLE' : 'AUTH_RATE_LIMITED',
      title: unavailable ? 'This identity action is temporarily unavailable.' : 'Too many identity attempts.',
    },
    {
      status: unavailable ? 503 : 429,
      headers: {
        'Cache-Control': 'no-store',
        ...(decision.retryAfterSeconds ? { 'Retry-After': String(decision.retryAfterSeconds) } : {}),
      },
    }
  );
}
