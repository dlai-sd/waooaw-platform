// Implements: architecture/reference/components/identity-boundary.md §11 Sign-out and account switch
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { getToken } from 'next-auth/jwt';
import { NextRequest, NextResponse } from 'next/server';

const sessionCookie = /^(?:(?:__Secure-|__Host-)?next-auth\.|waooaw[.-])/i;

function isSameOriginSubmission(request: NextRequest, applicationOrigin: string) {
  const origin = request.headers.get('origin');
  if (origin) return origin === applicationOrigin;

  if (request.headers.get('sec-fetch-site') === 'same-origin') return true;

  const referer = request.headers.get('referer');
  if (!referer) return false;
  try {
    return new URL(referer).origin === applicationOrigin;
  } catch {
    return false;
  }
}

export async function POST(request: NextRequest) {
  const applicationOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  if (!isSameOriginSubmission(request, applicationOrigin)) {
    return NextResponse.json({ code: 'IDENTITY_ACTION_DENIED', title: 'Sign out request was denied.' }, { status: 403 });
  }

  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
  const issuer = new URL(process.env.KEYCLOAK_ISSUER ?? 'http://localhost:8080/realms/waooaw');
  const logout = new URL(`${issuer.toString().replace(/\/$/, '')}/protocol/openid-connect/logout`);
  logout.searchParams.set('client_id', process.env.KEYCLOAK_CLIENT_ID ?? 'waooaw-web');
  logout.searchParams.set('post_logout_redirect_uri', new URL('/', applicationOrigin).toString());
  if (typeof token?.idToken === 'string') logout.searchParams.set('id_token_hint', token.idToken);

  const response = NextResponse.redirect(logout, 303);
  for (const cookie of request.cookies.getAll()) {
    if (sessionCookie.test(cookie.name)) response.cookies.delete(cookie.name);
  }
  response.headers.set('Cache-Control', 'no-store');
  return response;
}