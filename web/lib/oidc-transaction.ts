import { safeReturnTarget } from '@/lib/safe-return';
import type { OidcTransactionEnvelope } from '@/lib/web-session-store';

const providers = {
  'keycloak-google': 'GOOGLE',
  'keycloak-facebook': 'FACEBOOK',
  'keycloak-apple': 'APPLE',
  keycloak: 'EMAIL',
} as const;

export type OidcProviderClass = (typeof providers)[keyof typeof providers];

export function providerClassFromPath(pathname: string): OidcProviderClass | undefined {
  const provider = pathname.split('/').filter(Boolean).at(-1);
  return provider ? providers[provider as keyof typeof providers] : undefined;
}

export function normalizeOidcCallback(
  callbackUrl: string,
  requestedIntent: string,
  applicationOrigin: string
): Pick<OidcTransactionEnvelope, 'intent' | 'callbackPath'> | null {
  let callback: URL;
  try {
    callback = new URL(callbackUrl, applicationOrigin);
  } catch {
    return null;
  }
  if (
    callback.origin !== applicationOrigin ||
    callback.hash ||
    [...callback.searchParams.keys()].some((key) => key !== 'returnTo') ||
    callback.searchParams.getAll('returnTo').length > 1
  )
    return null;

  const returnTo = safeReturnTarget(callback.searchParams.get('returnTo') ?? undefined);
  const intent = requestedIntent.toUpperCase();
  if (intent === 'LOGIN' && ['/home', '/verify', '/account-link'].includes(callback.pathname))
    return {
      intent: 'LOGIN',
      callbackPath:
        callback.pathname === '/verify' && callback.searchParams.has('returnTo')
          ? `/verify?returnTo=${encodeURIComponent(returnTo)}`
          : callback.pathname,
    };
  if (
    (callback.pathname === '/login' && intent !== 'LOGIN') ||
    (callback.pathname === '/register' && !['REGISTER', 'TRIAL', 'HIRE'].includes(intent)) ||
    !['/login', '/register'].includes(callback.pathname)
  )
    return null;
  if (
    (intent === 'TRIAL' || intent === 'HIRE') &&
    new URL(returnTo, applicationOrigin).searchParams.get('intent') !== intent.toLowerCase()
  )
    return null;

  return {
    intent: intent as OidcTransactionEnvelope['intent'],
    callbackPath: `${callback.pathname}?returnTo=${encodeURIComponent(returnTo)}`,
  };
}

export function oidcProtocolCookies(headers: Headers): Record<string, string> {
  const combined = headers.get('set-cookie');
  const values =
    (
      headers as Headers & {
        getSetCookie?: () => string[];
      }
    ).getSetCookie?.() ?? (combined ? [combined] : []);
  const cookies: Record<string, string> = {};
  for (const header of values) {
    for (const candidate of header.split(/,(?=\s*(?:__Secure-|__Host-)?next-auth\.)/)) {
      const [pair] = candidate.trim().split(';', 1);
      const separator = pair.indexOf('=');
      if (separator < 1) continue;
      const name = pair.slice(0, separator);
      if (!/(?:state|nonce|pkce\.code_verifier)$/.test(name)) continue;
      cookies[name] = pair.slice(separator + 1);
    }
  }
  return cookies;
}

export function protocolCookiesMatch(
  expected: Record<string, string>,
  actual: { get(name: string): { value: string } | undefined }
): boolean {
  const entries = Object.entries(expected);
  return entries.length >= 2 && entries.every(([name, value]) => actual.get(name)?.value === value);
}
