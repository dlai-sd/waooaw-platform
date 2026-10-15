import { NextResponse } from 'next/server';
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
    if (
      !issuer ||
      !businessPlatform ||
      process.env.WEB_SESSION_CONFIG_DIGEST !== process.env.WEB_SESSION_EXPECTED_CONFIG_DIGEST ||
      process.env.WEB_SESSION_TELEMETRY_ROUTE_DIGEST !== process.env.WEB_SESSION_EXPECTED_TELEMETRY_ROUTE_DIGEST
    )
      throw new Error('Readiness configuration is incomplete');
    const [store, identity, membership] = await Promise.all([
      sessionStoreReady(),
      dependencyReady(`${issuer.replace(/\/$/, '')}/.well-known/openid-configuration`, 5_000),
      dependencyReady(`${businessPlatform.replace(/\/$/, '')}/health/ready`, 3_000),
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
