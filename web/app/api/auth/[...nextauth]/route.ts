import { randomUUID } from 'node:crypto';
import { authOptions } from '@/lib/auth';
import { enforceAuthAbuse } from '@/lib/auth-abuse-limiter';
import { withJourneyTrace } from '@/lib/journey-telemetry';
import {
  normalizeOidcCallback,
  oidcProtocolCookies,
  protocolCookiesMatch,
  providerClassFromPath,
} from '@/lib/oidc-transaction';
import { logServerFailure } from '@/lib/server-diagnostics';
import { type OidcTransactionEnvelope, consumeOidcTransaction, createOidcTransaction } from '@/lib/web-session-store';
import NextAuth from 'next-auth';
import { NextRequest, NextResponse } from 'next/server';

const handler = NextAuth(authOptions);
const browserBindingCookie = '__Host-waooaw-oidc-browser';

function dependencyUnavailable(correlationId: string) {
  return NextResponse.json(
    { code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', correlationId },
    { status: 503, headers: { 'Cache-Control': 'no-store' } }
  );
}

function deniedCallback(applicationOrigin: string) {
  const response = NextResponse.redirect(new URL('/auth/error?error=OAuthCallback', applicationOrigin), 303);
  response.headers.set('Cache-Control', 'no-store');
  return response;
}

async function initiationInput(request: NextRequest, applicationOrigin: string) {
  const form = await request
    .clone()
    .formData()
    .catch(() => null);
  if (!form) return null;
  const callbackUrl = form.get('callbackUrl');
  const intent = form.get('waooawIntent');
  return typeof callbackUrl === 'string' && typeof intent === 'string'
    ? normalizeOidcCallback(callbackUrl, intent, applicationOrigin)
    : null;
}

function transactionDenialReason(
  transaction: Awaited<ReturnType<typeof consumeOidcTransaction>>,
  state: string,
  providerClass: string,
  request: NextRequest
) {
  if (!transaction) return 'TRANSACTION_NOT_FOUND';
  if (transaction.state !== state) return 'STATE_MISMATCH';
  if (transaction.providerClass !== providerClass) return 'PROVIDER_MISMATCH';
  if (!protocolCookiesMatch(transaction.protocolCookies, request.cookies)) return 'PROTOCOL_COOKIES_MISMATCH';
  return undefined;
}

async function consumeCallbackTransaction(request: NextRequest): Promise<OidcTransactionEnvelope | null> {
  const state = request.nextUrl.searchParams.get('state');
  const browserBinding = request.cookies.get(browserBindingCookie)?.value;
  const providerClass = providerClassFromPath(request.nextUrl.pathname);
  if (!state || !browserBinding || !providerClass) {
    logServerFailure(
      'identity.callback.transaction_denied',
      undefined,
      {
        provider: providerClass ?? 'unknown',
        reason: state ? 'BROWSER_BINDING_ABSENT' : 'STATE_ABSENT',
      },
      'warn'
    );
    return null;
  }
  let transaction: Awaited<ReturnType<typeof consumeOidcTransaction>>;
  try {
    transaction = await consumeOidcTransaction(state, browserBinding);
  } catch (error) {
    logServerFailure('identity.oidc_transaction.consume_failed', error, { provider: providerClass });
    return null;
  }
  const reason = transactionDenialReason(transaction, state, providerClass, request);
  if (reason) {
    logServerFailure('identity.callback.transaction_denied', undefined, { provider: providerClass, reason }, 'warn');
    return null;
  }
  return transaction;
}

async function authenticatedResponse(...args: Parameters<typeof handler>) {
  const [rawRequest] = args;
  if (!(rawRequest instanceof NextRequest)) throw new TypeError('NextAuth request is invalid');
  const request = rawRequest;
  const applicationOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  const providerClass = providerClassFromPath(request.nextUrl.pathname);
  const isInitiation =
    request.method === 'POST' && request.nextUrl.pathname.includes('/api/auth/signin/') && providerClass;
  const isCallback =
    request.method === 'GET' && request.nextUrl.pathname.includes('/api/auth/callback/') && providerClass;
  if (isInitiation || isCallback) {
    const limited = await enforceAuthAbuse(request, isInitiation ? 'AUTH_START' : 'AUTH_CALLBACK');
    if (limited) return limited;
  }
  const initiation = isInitiation ? await initiationInput(request, applicationOrigin) : null;
  if (isInitiation && !initiation)
    return NextResponse.json(
      { code: 'IDENTITY_ACTION_DENIED' },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  const transaction = isCallback ? await consumeCallbackTransaction(request) : null;
  if (isCallback && !transaction) return deniedCallback(applicationOrigin);

  const response = await handler(...args);
  if (isInitiation && initiation && providerClass) {
    const result = (await response
      .clone()
      .json()
      .catch(() => null)) as { url?: unknown } | null;
    if (!result || typeof result.url !== 'string')
      return dependencyUnavailable(
        logServerFailure('identity.provider_start.redirect_missing', undefined, {
          provider: providerClass,
          upstreamStatus: response.status,
          hint: 'See the preceding nextauth.* record for the identity provider discovery or configuration error',
        })
      );
    const authorization = new URL(result.url);
    const state = authorization.searchParams.get('state');
    const protocolCookies = oidcProtocolCookies(response.headers);
    if (!state || Object.keys(protocolCookies).length < 2)
      return dependencyUnavailable(
        logServerFailure('identity.provider_start.protocol_incomplete', undefined, {
          provider: providerClass,
          statePresent: Boolean(state),
          protocolCookieCount: Object.keys(protocolCookies).length,
        })
      );
    const browserBinding = randomUUID();
    try {
      await createOidcTransaction(state, browserBinding, providerClass, {
        state,
        ...initiation,
        protocolCookies,
      });
    } catch (error) {
      return dependencyUnavailable(
        logServerFailure('identity.oidc_transaction.reserve_failed', error, { provider: providerClass })
      );
    }
    const secured = new NextResponse(response.body, {
      status: response.status,
      headers: response.headers,
    });
    secured.cookies.set(browserBindingCookie, browserBinding, {
      httpOnly: true,
      maxAge: 10 * 60,
      path: '/',
      sameSite: 'lax',
      secure: applicationOrigin.startsWith('https://'),
    });
    secured.headers.set('Cache-Control', 'no-store, max-age=0');
    secured.headers.set('Pragma', 'no-cache');
    return secured;
  }
  if (isCallback && transaction) {
    const location = response.headers.get('location');
    if (location) {
      const destination = new URL(location, applicationOrigin);
      if (
        destination.origin === applicationOrigin &&
        !destination.pathname.startsWith('/api/auth/error') &&
        destination.pathname !== '/auth/error'
      ) {
        const headers = new Headers(response.headers);
        headers.set('Location', new URL(transaction.callbackPath, applicationOrigin).toString());
        const routed = new NextResponse(response.body, {
          status: response.status,
          headers,
        });
        routed.cookies.set(browserBindingCookie, '', {
          expires: new Date(0),
          path: '/',
        });
        routed.headers.set('Cache-Control', 'no-store, max-age=0');
        routed.headers.set('Pragma', 'no-cache');
        return routed;
      }
    }
  }
  response.headers.set('Cache-Control', 'no-store, max-age=0');
  response.headers.set('Pragma', 'no-cache');
  return response;
}

export const GET = (...args: Parameters<typeof handler>) =>
  withJourneyTrace('identity.login', () => authenticatedResponse(...args));
export const POST = (...args: Parameters<typeof handler>) =>
  withJourneyTrace('identity.login', () => authenticatedResponse(...args));
