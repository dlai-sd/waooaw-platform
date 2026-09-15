// Implements: architecture/reference/components/identity-boundary.md §11 Sign-out and account switch
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { getToken } from 'next-auth/jwt';
import { NextRequest, NextResponse } from 'next/server';

const sessionCookie = /^(?:(?:__Secure-|__Host-)?next-auth\.|waooaw[.-])/i;
const logoutContinuationCookie = 'waooaw.logout-continuation';

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

async function keycloakLogoutUrl(request: NextRequest, applicationOrigin: string) {
  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
  const issuer = new URL(process.env.KEYCLOAK_ISSUER ?? 'http://localhost:8080/realms/waooaw');
  const logout = new URL(`${issuer.toString().replace(/\/$/, '')}/protocol/openid-connect/logout`);
  logout.searchParams.set('client_id', process.env.KEYCLOAK_CLIENT_ID ?? 'waooaw-web');
  logout.searchParams.set('post_logout_redirect_uri', new URL('/', applicationOrigin).toString());
  if (typeof token?.idToken === 'string') logout.searchParams.set('id_token_hint', token.idToken);
  return logout;
}

function clearSessionCookies(response: NextResponse, request: NextRequest) {
  for (const cookie of request.cookies.getAll()) {
    if (!sessionCookie.test(cookie.name)) continue;
    if (cookie.name === logoutContinuationCookie) {
      response.cookies.set(cookie.name, '', { expires: new Date(0), path: '/api/auth/keycloak-logout' });
    } else {
      response.cookies.delete(cookie.name);
    }
  }
  response.headers.set('Cache-Control', 'no-store');
  return response;
}

export async function POST(request: NextRequest) {
  const applicationOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  if (!isSameOriginSubmission(request, applicationOrigin)) {
    return NextResponse.json({ code: 'IDENTITY_ACTION_DENIED', title: 'Sign out request was denied.' }, { status: 403 });
  }

  if (request.headers.get('accept')?.includes('application/json')) {
    const nonce = crypto.randomUUID();
    const logoutPath = `/api/auth/keycloak-logout?nonce=${encodeURIComponent(nonce)}`;
    const response = NextResponse.json({ logoutPath });
    response.cookies.set(logoutContinuationCookie, nonce, {
      httpOnly: true,
      maxAge: 60,
      path: '/api/auth/keycloak-logout',
      sameSite: 'strict',
      secure: applicationOrigin.startsWith('https://'),
    });
    response.headers.set('Cache-Control', 'no-store');
    return response;
  }

  const logout = await keycloakLogoutUrl(request, applicationOrigin);
  return clearSessionCookies(NextResponse.redirect(logout, 303), request);
}

export async function GET(request: NextRequest) {
  const nonce = request.nextUrl.searchParams.get('nonce');
  if (!nonce || request.cookies.get(logoutContinuationCookie)?.value !== nonce) {
    return NextResponse.json({ code: 'IDENTITY_ACTION_DENIED', title: 'Sign out request was denied.' }, { status: 403 });
  }

  const applicationOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  const logout = await keycloakLogoutUrl(request, applicationOrigin);
  return clearSessionCookies(NextResponse.redirect(logout, 303), request);
}