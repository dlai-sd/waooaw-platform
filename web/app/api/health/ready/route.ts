import { NextResponse } from 'next/server';
import { authAbuseLimiterStatus } from '@/lib/auth-abuse-limiter';
import { serverSessionMode } from '@/lib/server-session-mode';
import { oidcTransactionStoreReady, sessionStoreReady } from '@/lib/web-session-store';

async function dependencyReady(url: string, timeoutMs: number): Promise<boolean> {
  const response = await fetch(url, {
    cache: 'no-store',
    signal: AbortSignal.timeout(timeoutMs),
  });
  return response.ok;
}

export async function GET() {
  try {
    const issuer = process.env.KEYCLOAK_ISSUER;
    const readinessIssuer = process.env.KEYCLOAK_READINESS_ISSUER;
    const businessPlatform = process.env.BUSINESS_PLATFORM_URL;
    const mode = serverSessionMode();
    if (!issuer || !readinessIssuer || !businessPlatform) throw new Error('Readiness configuration is incomplete');
    if (mode !== 'disabled') {
      const configDigest = process.env.WEB_SESSION_CONFIG_DIGEST;
      const expectedConfigDigest = process.env.WEB_SESSION_EXPECTED_CONFIG_DIGEST;
      const telemetryRouteDigest = process.env.WEB_SESSION_TELEMETRY_ROUTE_DIGEST;
      const expectedTelemetryRouteDigest = process.env.WEB_SESSION_EXPECTED_TELEMETRY_ROUTE_DIGEST;
      if (
        !configDigest ||
        !expectedConfigDigest ||
        !telemetryRouteDigest ||
        !expectedTelemetryRouteDigest ||
        configDigest !== expectedConfigDigest ||
        telemetryRouteDigest !== expectedTelemetryRouteDigest
      ) {
        throw new Error('Session readiness configuration is incomplete');
      }
    }

    const [identity, membership, limiter, transactionStore, sessionStore] = await Promise.all([
      dependencyReady(`${readinessIssuer.replace(/\/$/, '')}/.well-known/openid-configuration`, 5_000),
      dependencyReady(`${businessPlatform.replace(/\/$/, '')}/health/ready`, 3_000),
      authAbuseLimiterStatus(),
      mode === 'disabled' ? oidcTransactionStoreReady() : Promise.resolve(true),
      mode === 'disabled' ? Promise.resolve(true) : sessionStoreReady(),
    ]);
    if (!sessionStore || !transactionStore || !limiter.ready || !identity || !membership) {
      return NextResponse.json(
        {
          code: 'REVISION_NOT_READY',
          dependencies: { identity, membership, transactionStore, sessionStore, limiter },
        },
        {
          status: 503,
          headers: {
            'Cache-Control': 'no-store',
            ...(limiter.retryAfterSeconds ? { 'Retry-After': String(limiter.retryAfterSeconds) } : {}),
          },
        }
      );
    }
    return new NextResponse(null, {
      status: 204,
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch {
    return NextResponse.json({ code: 'REVISION_NOT_READY' }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
}
