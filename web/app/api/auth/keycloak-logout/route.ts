// Implements: architecture/reference/components/identity-boundary.md §11 Sign-out and account switch
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { getToken } from 'next-auth/jwt';
import { type NextRequest, NextResponse } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { recordWebIdentitySecurityEvent } from '@/lib/identity-security-events';

const sessionCookie = /^(?:(?:__Secure-|__Host-)?next-auth\.|waooaw[.-])/i;
const logoutContinuationCookie = 'waooaw.logout-continuation';
const logoutCorrelationCookie = 'waooaw.logout-correlation';

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

async function revokeWaooawSessions(request: NextRequest) {
  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
  const accessToken = token ? activeAccessToken(token) : undefined;
  if (!accessToken) return false;

  try {
    const response = await fetch(
      `${process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001'}/api/v1/identity/sessions`,
      {
        method: 'DELETE',
        headers: {
          Accept: 'application/json',
          Authorization: `Bearer ${accessToken}`,
          'Idempotency-Key': crypto.randomUUID(),
        },
        cache: 'no-store',
      }
    );
    if (!response.ok) {
      console.error('WAOOAW session revocation was not confirmed.', { status: response.status });
      return false;
    }
    return true;
  } catch (error) {
    console.error('WAOOAW session revocation was not confirmed.', {
      reason: error instanceof Error ? error.name : 'UnknownError',
    });
    return false;
  }
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
    return NextResponse.json(
      { code: 'IDENTITY_ACTION_DENIED', title: 'Sign out request was denied.' },
      { status: 403 }
    );
  }

  if (request.headers.get('accept')?.includes('application/json')) {
    const correlationId = crypto.randomUUID();
    await recordWebIdentitySecurityEvent({
      correlationId, eventType: 'LOGOUT_REQUEST', providerClass: 'INTERNAL', outcome: 'ATTEMPTED',
      reasonCode: 'CUSTOMER_REQUESTED', assuranceClass: 'AAL2',
    });
    const revoked = await revokeWaooawSessions(request);
    if (!revoked)
      await recordWebIdentitySecurityEvent({
        correlationId, eventType: 'LOGOUT_FAILURE', providerClass: 'INTERNAL', outcome: 'FAILED',
        reasonCode: 'SESSION_REVOCATION_UNCONFIRMED', assuranceClass: 'AAL2',
      });
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
    response.cookies.set(logoutCorrelationCookie, correlationId, {
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
    return NextResponse.json(
      { code: 'IDENTITY_ACTION_DENIED', title: 'Sign out request was denied.' },
      { status: 403 }
    );
  }

  const applicationOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  const correlationId = request.cookies.get(logoutCorrelationCookie)?.value;
  if (correlationId) {
    await recordWebIdentitySecurityEvent({
      correlationId, eventType: 'LOGOUT_COMPLETION', providerClass: 'INTERNAL', outcome: 'SUCCEEDED',
      reasonCode: 'LOCAL_SESSION_CLEARED', assuranceClass: 'ANONYMOUS',
    });
  }
  const logout = await keycloakLogoutUrl(request, applicationOrigin);
  const response = clearSessionCookies(NextResponse.redirect(logout, 303), request);
  response.cookies.set(logoutCorrelationCookie, '', {
    expires: new Date(0),
    path: '/api/auth/keycloak-logout',
  });
  return response;
}
