import { type NextRequest, NextResponse } from 'next/server';
import {
  isAuthorizedAzureVaultToken,
  isKeyVaultPortalAdministrator,
  isValidSecretName,
  keyVaultTarget,
} from '@/lib/key-vault-admin';
import { accessTokenFromRequest } from '@/lib/server-auth';

const MAX_SECRET_VALUE_LENGTH = 16_384;
const writeWindows = new Map<string, number[]>();

function sameOrigin(request: NextRequest): boolean {
  const fetchSite = request.headers.get('sec-fetch-site');
  if (fetchSite) return fetchSite === 'same-origin';
  const origin = request.headers.get('origin');
  const expectedOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  if (origin) {
    try {
      return new URL(origin).origin === expectedOrigin;
    } catch {
      return false;
    }
  }
  const referer = request.headers.get('referer');
  if (!referer) return false;
  try {
    return new URL(referer).origin === expectedOrigin;
  } catch {
    return false;
  }
}

function withinWriteLimit(subject: string, now = Date.now()): boolean {
  const recent = (writeWindows.get(subject) ?? []).filter((timestamp) => now - timestamp < 60_000);
  if (recent.length >= 5) return false;
  recent.push(now);
  writeWindows.set(subject, recent);
  return true;
}

export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) {
    return NextResponse.json({ title: 'Request origin is not permitted.' }, { status: 403 });
  }
  const portalAccessToken = await accessTokenFromRequest(request);
  if (!portalAccessToken || !isKeyVaultPortalAdministrator(portalAccessToken)) {
    return NextResponse.json({ title: 'Azure Key Vault administration is not permitted.' }, { status: 403 });
  }
  const target = keyVaultTarget();
  if (!target) {
    return NextResponse.json({ title: 'Azure Key Vault is unavailable in this environment.' }, { status: 503 });
  }
  const authorization = request.headers.get('authorization');
  const azureAccessToken = authorization?.startsWith('Bearer ') ? authorization.slice(7) : '';
  if (!azureAccessToken || !isAuthorizedAzureVaultToken(azureAccessToken, target)) {
    return NextResponse.json({ title: 'Sign in to Azure with the authorized administrator account.' }, { status: 403 });
  }
  const body = (await request.json().catch(() => undefined)) as { name?: unknown; value?: unknown } | undefined;
  const name = typeof body?.name === 'string' ? body.name.trim() : '';
  const value = typeof body?.value === 'string' ? body.value : '';
  if (!isValidSecretName(name) || value.length < 1 || value.length > MAX_SECRET_VALUE_LENGTH) {
    return NextResponse.json({ title: 'Secret name or value is invalid.' }, { status: 400 });
  }
  const subject = `${target.environment}:${name}`;
  if (!withinWriteLimit(subject)) {
    return NextResponse.json({ title: 'Too many writes. Wait before trying again.' }, { status: 429 });
  }
  const response = await fetch(`${target.vaultUrl}/secrets/${encodeURIComponent(name)}?api-version=7.4`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${azureAccessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      value,
      tags: {
        environment: target.environment,
        updatedVia: 'waooaw-customer-portal',
      },
    }),
    cache: 'no-store',
  });
  if (!response.ok) {
    return NextResponse.json(
      { title: response.status === 403 ? 'Azure denied this write.' : 'Azure Key Vault could not save the secret.' },
      { status: response.status === 403 ? 403 : 502 }
    );
  }
  return NextResponse.json(
    { name, environment: target.environment, status: 'SAVED' },
    { headers: { 'Cache-Control': 'no-store' } }
  );
}
