import 'server-only';

// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PRIV-01
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { cookies, headers } from 'next/headers';
import { getToken } from 'next-auth/jwt';
import type { NextRequest } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { loadSession } from '@/lib/web-session-store';
import { serverSessionMode } from '@/lib/server-session-mode';

export async function sessionTokenFromRequest(request: NextRequest) {
  if (serverSessionMode() !== 'enforced')
    return getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });
  return getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
    cookieName: '__Host-waooaw-session',
    decode: async ({ token }) => (token ? loadSession(token) : null),
  });
}

export async function accessTokenFromRequest(request: NextRequest): Promise<string | undefined> {
  const token = await sessionTokenFromRequest(request);
  return token ? activeAccessToken(token) : undefined;
}

export async function getServerAccessToken(): Promise<string | undefined> {
  const token = await getServerSessionToken();
  return token ? activeAccessToken(token) : undefined;
}

export async function getServerSessionToken() {
  const [requestCookies, requestHeaders] = await Promise.all([cookies(), headers()]);
  const request = { cookies: requestCookies, headers: requestHeaders } as unknown as NextRequest;
  return sessionTokenFromRequest(request);
}
