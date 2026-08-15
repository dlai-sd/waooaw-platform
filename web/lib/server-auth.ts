import 'server-only';

// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-PRIV-01
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { headers } from 'next/headers';
import { getToken } from 'next-auth/jwt';
import { NextRequest } from 'next/server';

export async function accessTokenFromRequest(request: NextRequest): Promise<string | undefined> {
  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
  return typeof token?.accessToken === 'string' ? token.accessToken : undefined;
}

export async function getServerAccessToken(): Promise<string | undefined> {
  const request = new NextRequest(process.env.NEXTAUTH_URL ?? 'http://localhost:3000', { headers: new Headers(await headers()) });
  return accessTokenFromRequest(request);
}