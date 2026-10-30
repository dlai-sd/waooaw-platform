// Implements: architecture/reference/components/identity-boundary.md §11 Sign-out and account switch
// Implements: work-contracts/WC-119-auth-session-account-switch-recovery.md WC119-R002, WC119-R003
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { recordWebIdentitySecurityEvent } from '@/lib/identity-security-events';
import { withJourneyTrace } from '@/lib/journey-telemetry';
import { isSameOriginRequest } from '@/lib/same-origin-request';
import { logServerFailure } from '@/lib/server-diagnostics';
import { loadSession, revokeSession } from '@/lib/web-session-store';
import { decode, encode, getToken } from 'next-auth/jwt';
import { type NextRequest, NextResponse } from 'next/server';

const sessionCookie = /^(?:__Host-waooaw-session|(?:(?:__Secure-|__Host-)?next-auth\.|waooaw[.-]))/i;
const logoutContinuationCookie = 'waooaw.logout-continuation';
const logoutCorrelationCookie = 'waooaw.logout-correlation';
const logoutCommandCookie = 'waooaw.logout-command';
const logoutProviderCookie = 'waooaw.logout-provider';
const logoutHintCookie = 'waooaw.logout-hint';
const normalLogoutState = 'waooaw-home-after-logout';
const registrationLogoutState = 'waooaw-register-after-logout';
type LogoutCommand = 'LOCAL_LOGOUT' | 'ACCOUNT_SWITCH' | 'REGISTRATION';
type RegistrationProvider = 'GOOGLE' | 'FACEBOOK';

function reportOriginDenial(request: NextRequest, applicationOrigin: string) {
  const referer = request.headers.get('referer');
  let refererOrigin: string | undefined;
  try {
    refererOrigin = referer ? new URL(referer).origin : undefined;
  } catch {
    refererOrigin = 'invalid';
  }
  console.warn('Identity action origin denied', {
    applicationOrigin,
    forwardedHost: request.headers.get('x-forwarded-host'),
    forwardedProto: request.headers.get('x-forwarded-proto'),
    origin: request.headers.get('origin'),
    refererOrigin,
    requestOrigin: request.nextUrl.origin,
    secFetchSite: request.headers.get('sec-fetch-site'),
  });
}

async function sessionToken(request: NextRequest) {
  return getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
    cookieName: '__Host-waooaw-session',
    decode: async ({ token: handle }) => (handle ? loadSession(handle) : null),
  });
}

function keycloakLogoutUrl(
  applicationOrigin: string,
  command: LogoutCommand,
  provider?: RegistrationProvider,
  idToken?: string
) {
  const issuer = new URL(process.env.KEYCLOAK_ISSUER ?? 'http://localhost:8080/realms/waooaw');
  const logout = new URL(`${issuer.toString().replace(/\/$/, '')}/protocol/openid-connect/logout`);
  logout.searchParams.set('client_id', process.env.KEYCLOAK_CLIENT_ID ?? 'waooaw-web');
  logout.searchParams.set('post_logout_redirect_uri', new URL('/login', applicationOrigin).toString());
  if (command === 'LOCAL_LOGOUT') logout.searchParams.set('state', normalLogoutState);
  if (command === 'REGISTRATION' && provider)
    logout.searchParams.set('state', `${registrationLogoutState}:${provider}`);
  if (idToken) logout.searchParams.set('id_token_hint', idToken);
  return logout;
}

async function revokeOwnedSession(request: NextRequest, command: LogoutCommand) {
  try {
    const token = await sessionToken(request);
    if (!token) return { status: 'not-applicable' } as const;
    await revokeSession(token, command === 'ACCOUNT_SWITCH' ? 'ACCOUNT_SWITCH' : 'CUSTOMER_LOGOUT');
    return { status: 'confirmed', idToken: token.idToken } as const;
  } catch (error) {
    logServerFailure('identity.logout.revocation_failed', error, { command });
    return { status: 'unconfirmed' } as const;
  }
}

function clearSessionCookies(response: NextResponse, request: NextRequest) {
  for (const cookie of request.cookies.getAll()) {
    if (!sessionCookie.test(cookie.name)) continue;
    if (
      cookie.name === logoutContinuationCookie ||
      cookie.name === logoutCorrelationCookie ||
      cookie.name === logoutCommandCookie ||
      cookie.name === logoutProviderCookie ||
      cookie.name === logoutHintCookie
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
  if (!isSameOriginRequest(request, applicationOrigin)) {
    reportOriginDenial(request, applicationOrigin);
    return NextResponse.json(
      { code: 'IDENTITY_ACTION_DENIED', title: 'Sign out request was denied.' },
      { status: 403 }
    );
  }

  if (!request.headers.get('accept')?.includes('application/json')) {
    const revoked = await revokeOwnedSession(request, 'LOCAL_LOGOUT');
    if (revoked.status === 'unconfirmed') return revocationFailure(request, crypto.randomUUID());
    const logout = keycloakLogoutUrl(applicationOrigin, 'LOCAL_LOGOUT', undefined, revoked.idToken);
    return clearSessionCookies(NextResponse.redirect(logout, 303), request);
  }

  const input = (await request.json().catch(() => null)) as {
    command?: unknown;
    provider?: unknown;
  } | null;
  const command: LogoutCommand =
    input?.command === 'ACCOUNT_SWITCH' || input?.command === 'REGISTRATION' ? input.command : 'LOCAL_LOGOUT';
  const provider: RegistrationProvider | undefined =
    input?.provider === 'GOOGLE' || input?.provider === 'FACEBOOK' ? input.provider : undefined;
  if (command === 'REGISTRATION' && !provider)
    return NextResponse.json(
      {
        code: 'IDENTITY_ACTION_DENIED',
        title: 'Registration session reset was denied.',
      },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  const correlationId = crypto.randomUUID();
  await recordWebIdentitySecurityEvent({
    correlationId,
    eventType: 'LOGOUT_REQUEST',
    providerClass: 'INTERNAL',
    outcome: 'ATTEMPTED',
    reasonCode: 'CUSTOMER_REQUESTED',
    assuranceClass: 'AAL2',
  });
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) throw new Error('NEXTAUTH_SECRET is required for the logout continuation');
  const revoked = await revokeOwnedSession(request, command);
  if (revoked.status === 'unconfirmed') return revocationFailure(request, correlationId);

  const nonce = crypto.randomUUID();
  const hint = await encode({
    secret,
    salt: logoutHintCookie,
    maxAge: 60,
    token: { nonce, idToken: revoked.idToken },
  });
  const response = NextResponse.json({
    logoutPath: `/api/auth/keycloak-logout?nonce=${encodeURIComponent(nonce)}`,
  });
  const continuationCookies = [
    [logoutContinuationCookie, nonce],
    [logoutCorrelationCookie, correlationId],
    [logoutCommandCookie, command],
    [logoutHintCookie, hint],
    ...(provider ? [[logoutProviderCookie, provider]] : []),
  ];
  for (const [name, value] of continuationCookies) {
    response.cookies.set(name, value, {
      httpOnly: true,
      maxAge: 60,
      path: '/api/auth/keycloak-logout',
      sameSite: 'lax',
      secure: applicationOrigin.startsWith('https://'),
    });
  }
  response.headers.set('Cache-Control', 'no-store');
  return response;
}

async function logoutGet(request: NextRequest) {
  const nonce = request.nextUrl.searchParams.get('nonce');
  if (!nonce || request.cookies.get(logoutContinuationCookie)?.value !== nonce)
    return clearSessionCookies(
      NextResponse.json(
        {
          code: 'IDENTITY_ACTION_DENIED',
          title: 'Sign out request was denied.',
        },
        { status: 403 }
      ),
      request
    );

  const hint = request.cookies.get(logoutHintCookie)?.value;
  let idToken: string | undefined;
  try {
    const secret = process.env.NEXTAUTH_SECRET;
    if (!secret) throw new Error('NEXTAUTH_SECRET is required for the logout continuation');
    const continuation = hint ? await decode({ secret, salt: logoutHintCookie, token: hint }) : null;
    if (
      !continuation ||
      continuation.nonce !== nonce ||
      typeof continuation.exp !== 'number' ||
      continuation.exp <= Math.floor(Date.now() / 1000)
    )
      return clearSessionCookies(
        NextResponse.json(
          {
            code: 'IDENTITY_ACTION_DENIED',
            title: 'Sign out request was denied.',
          },
          { status: 403 }
        ),
        request
      );
    idToken = typeof continuation.idToken === 'string' ? continuation.idToken : undefined;
  } catch {
    logServerFailure('identity.logout.continuation_invalid', new Error('Logout continuation is invalid or expired'));
    return clearSessionCookies(
      NextResponse.json(
        {
          code: 'IDENTITY_ACTION_DENIED',
          title: 'Sign out request was denied.',
        },
        { status: 403 }
      ),
      request
    );
  }

  const applicationOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  const command =
    request.cookies.get(logoutCommandCookie)?.value === 'ACCOUNT_SWITCH' ||
    request.cookies.get(logoutCommandCookie)?.value === 'REGISTRATION'
      ? (request.cookies.get(logoutCommandCookie)?.value as LogoutCommand)
      : 'LOCAL_LOGOUT';
  const providerValue = request.cookies.get(logoutProviderCookie)?.value;
  const provider: RegistrationProvider | undefined =
    providerValue === 'GOOGLE' || providerValue === 'FACEBOOK' ? providerValue : undefined;
  if (command === 'REGISTRATION' && !provider)
    return clearSessionCookies(
      NextResponse.json(
        {
          code: 'IDENTITY_ACTION_DENIED',
          title: 'Registration session reset was denied.',
        },
        { status: 403 }
      ),
      request
    );
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

  const logout = keycloakLogoutUrl(applicationOrigin, command, provider, idToken);
  return clearSessionCookies(NextResponse.redirect(logout, 303), request);
}

export const POST = (request: NextRequest) => withJourneyTrace('identity.logout', () => logoutPost(request));
export const GET = (request: NextRequest) => withJourneyTrace('identity.logout', () => logoutGet(request));
