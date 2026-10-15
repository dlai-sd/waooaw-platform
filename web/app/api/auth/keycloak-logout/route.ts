// Implements: architecture/reference/components/identity-boundary.md §11 Sign-out and account switch
// Implements: work-contracts/WC-119-auth-session-account-switch-recovery.md WC119-R002, WC119-R003
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { recordWebIdentitySecurityEvent } from '@/lib/identity-security-events';
import { withJourneyTrace } from '@/lib/journey-telemetry';
import { loadSession, revokeSession } from '@/lib/web-session-store';
import { getToken } from 'next-auth/jwt';
import { type NextRequest, NextResponse } from 'next/server';

const sessionCookie = /^(?:__Host-waooaw-session|(?:(?:__Secure-|__Host-)?next-auth\.|waooaw[.-]))/i;
const logoutContinuationCookie = 'waooaw.logout-continuation';
const logoutCorrelationCookie = 'waooaw.logout-correlation';
const logoutCommandCookie = 'waooaw.logout-command';
type LogoutCommand = 'LOCAL_LOGOUT' | 'ACCOUNT_SWITCH';

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

async function sessionToken(request: NextRequest) {
  return getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
    cookieName: '__Host-waooaw-session',
    decode: async ({ token: handle }) => (handle ? loadSession(handle) : null),
  });
}

async function keycloakLogoutUrl(request: NextRequest, applicationOrigin: string, command: LogoutCommand) {
  const token = await sessionToken(request);
  const issuer = new URL(process.env.KEYCLOAK_ISSUER ?? 'http://localhost:8080/realms/waooaw');
  const logout = new URL(`${issuer.toString().replace(/\/$/, '')}/protocol/openid-connect/logout`);
  logout.searchParams.set('client_id', process.env.KEYCLOAK_CLIENT_ID ?? 'waooaw-web');
  logout.searchParams.set(
    'post_logout_redirect_uri',
    new URL(command === 'ACCOUNT_SWITCH' ? '/login?accountSwitch=1' : '/login', applicationOrigin).toString()
  );
  if (typeof token?.idToken === 'string') logout.searchParams.set('id_token_hint', token.idToken);
  return logout;
}

async function revokeOwnedSession(request: NextRequest, command: LogoutCommand) {
  const token = await sessionToken(request);
  if (!token) return 'not-applicable' as const;

  try {
    await revokeSession(token, command === 'ACCOUNT_SWITCH' ? 'ACCOUNT_SWITCH' : 'CUSTOMER_LOGOUT');
    return 'confirmed' as const;
  } catch {
    return 'unconfirmed' as const;
  }
}

function clearSessionCookies(response: NextResponse, request: NextRequest) {
  for (const cookie of request.cookies.getAll()) {
    if (!sessionCookie.test(cookie.name)) continue;
    if (
      cookie.name === logoutContinuationCookie ||
      cookie.name === logoutCorrelationCookie ||
      cookie.name === logoutCommandCookie
    ) {
      response.cookies.set(cookie.name, '', {
        expires: new Date(0),
        path: '/api/auth/keycloak-logout',
      });
    } else {
      response.cookies.delete(cookie.name);
    }
  }
  response.headers.set('Cache-Control', 'no-store');
  return response;
}

async function revocationFailure(request: NextRequest, correlationId: string) {
  await recordWebIdentitySecurityEvent({
    correlationId,
    eventType: 'LOGOUT_FAILURE',
    providerClass: 'INTERNAL',
    outcome: 'FAILED',
    reasonCode: 'SESSION_REVOCATION_UNCONFIRMED',
    assuranceClass: 'AAL2',
  });
  return clearSessionCookies(
    NextResponse.json(
      {
        code: 'SESSION_REVOCATION_UNCONFIRMED',
        title: 'Sign out could not be completed.',
      },
      { status: 503 }
    ),
    request
  );
}

async function logoutPost(request: NextRequest) {
  const applicationOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  if (!isSameOriginSubmission(request, applicationOrigin))
    return NextResponse.json(
      { code: 'IDENTITY_ACTION_DENIED', title: 'Sign out request was denied.' },
      { status: 403 }
    );

  if (!request.headers.get('accept')?.includes('application/json')) {
    const logout = await keycloakLogoutUrl(request, applicationOrigin, 'LOCAL_LOGOUT');
    await revokeOwnedSession(request, 'LOCAL_LOGOUT');
    return clearSessionCookies(NextResponse.redirect(logout, 303), request);
  }

  const input = (await request.json().catch(() => null)) as { command?: unknown } | null;
  const command: LogoutCommand = input?.command === 'ACCOUNT_SWITCH' ? 'ACCOUNT_SWITCH' : 'LOCAL_LOGOUT';
  const correlationId = crypto.randomUUID();
  await recordWebIdentitySecurityEvent({
    correlationId,
    eventType: 'LOGOUT_REQUEST',
    providerClass: 'INTERNAL',
    outcome: 'ATTEMPTED',
    reasonCode: 'CUSTOMER_REQUESTED',
    assuranceClass: 'AAL2',
  });
  if ((await revokeOwnedSession(request, command)) === 'unconfirmed') return revocationFailure(request, correlationId);

  const nonce = crypto.randomUUID();
  const response = NextResponse.json({
    logoutPath: `/api/auth/keycloak-logout?nonce=${encodeURIComponent(nonce)}`,
  });
  for (const [name, value] of [
    [logoutContinuationCookie, nonce],
    [logoutCorrelationCookie, correlationId],
    [logoutCommandCookie, command],
  ]) {
    response.cookies.set(name, value, {
      httpOnly: true,
      maxAge: 60,
      path: '/api/auth/keycloak-logout',
      sameSite: 'strict',
      secure: applicationOrigin.startsWith('https://'),
    });
  }
  response.headers.set('Cache-Control', 'no-store');
  return response;
}

async function logoutGet(request: NextRequest) {
  const nonce = request.nextUrl.searchParams.get('nonce');
  if (!nonce || request.cookies.get(logoutContinuationCookie)?.value !== nonce)
    return NextResponse.json(
      { code: 'IDENTITY_ACTION_DENIED', title: 'Sign out request was denied.' },
      { status: 403 }
    );

  const applicationOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  const command =
    request.cookies.get(logoutCommandCookie)?.value === 'ACCOUNT_SWITCH' ? 'ACCOUNT_SWITCH' : 'LOCAL_LOGOUT';
  const correlationId = request.cookies.get(logoutCorrelationCookie)?.value;
  if (correlationId)
    await recordWebIdentitySecurityEvent({
      correlationId,
      eventType: 'LOGOUT_REQUEST',
      providerClass: 'INTERNAL',
      outcome: 'ATTEMPTED',
      reasonCode: 'IDP_LOGOUT_REDIRECT_STARTED',
      assuranceClass: 'ANONYMOUS',
    });

  const logout = await keycloakLogoutUrl(request, applicationOrigin, command);
  return clearSessionCookies(NextResponse.redirect(logout, 303), request);
}

export const POST = (request: NextRequest) => withJourneyTrace('identity.logout', () => logoutPost(request));
export const GET = (request: NextRequest) => withJourneyTrace('identity.logout', () => logoutGet(request));
