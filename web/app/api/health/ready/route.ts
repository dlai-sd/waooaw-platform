import { NextResponse } from 'next/server';
import { serverSessionMode } from '@/lib/server-session-mode';
import { sessionStoreReady } from '@/lib/web-session-store';

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
    const businessPlatform = process.env.BUSINESS_PLATFORM_URL;
    const mode = serverSessionMode();
    if (!issuer || !businessPlatform) throw new Error('Readiness configuration is incomplete');
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

    const [identity, membership, store] = await Promise.all([
      dependencyReady(`${issuer.replace(/\/$/, '')}/.well-known/openid-configuration`, 5_000),
      dependencyReady(`${businessPlatform.replace(/\/$/, '')}/health/ready`, 3_000),
      mode === 'disabled' ? Promise.resolve(true) : sessionStoreReady(),
    ]);
    if (!store || !identity || !membership) throw new Error('A mandatory dependency is unready');
    return new NextResponse(null, {
      status: 204,
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch {
    return NextResponse.json({ code: 'REVISION_NOT_READY' }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
}
