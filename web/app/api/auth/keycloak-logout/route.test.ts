/** @jest-environment node */

jest.mock('next-auth/jwt', () => ({
  ...jest.requireActual('next-auth/jwt'),
  getToken: jest.fn(),
}));
jest.mock('@/lib/identity-security-events', () => ({
  recordWebIdentitySecurityEvent: jest.fn(),
}));
jest.mock('@/lib/web-session-store', () => ({
  loadSession: jest.fn(),
  revokeSession: jest.fn(),
}));
jest.mock('server-only', () => ({}));
jest.mock('@/lib/auth', () => ({ activeAccessToken: jest.fn() }));

import { recordWebIdentitySecurityEvent } from '@/lib/identity-security-events';
import { loadSession, revokeSession } from '@/lib/web-session-store';
import { encode, getToken } from 'next-auth/jwt';
import { NextRequest } from 'next/server';
import { GET, POST } from './route';

const testSecret = 'test-secret';
const originalEnvironment = process.env;

function requiredHeader(response: Response, name: string): string {
  const value = response.headers.get(name);
  expect(value).not.toBeNull();
  return value ?? '';
}

function browserCookies(response: Response): string {
  return response.headers
    .getSetCookie()
    .map((cookie) => cookie.split(';')[0])
    .join('; ');
}

describe('Keycloak logout route', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env = { ...originalEnvironment };
    global.fetch = jest.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    process.env.KEYCLOAK_ISSUER = 'https://identity.example/realms/waooaw';
    process.env.KEYCLOAK_CLIENT_ID = 'waooaw-web';
    process.env.NEXTAUTH_URL = 'https://app.example';
    process.env.NEXTAUTH_SECRET = testSecret;
    process.env.WAOOAW_SERVER_SESSION_MODE = 'enforced';
    jest.mocked(getToken).mockResolvedValue({ idToken: 'server-held-id-token' });
  });

  afterEach(() => {
    process.env = originalEnvironment;
  });

  it.each(['disabled', 'shadow', 'enforced'] as const)(
    'preserves the ID token from a real %s session cookie after POST then GET',
    async (mode) => {
      process.env.WAOOAW_SERVER_SESSION_MODE = mode;
      const actualJwt = jest.requireActual<typeof import('next-auth/jwt')>('next-auth/jwt');
      jest.mocked(getToken).mockImplementation(actualJwt.getToken);
      jest.mocked(loadSession).mockResolvedValue({
        sessionFamilyId: 'owned-family',
        idToken: 'real-cookie-id-token',
      });
      const cookieName = mode === 'enforced' ? '__Host-waooaw-session' : '__Secure-next-auth.session-token';
      const session =
        mode === 'enforced'
          ? 'opaque-session-handle'
          : await encode({
              secret: testSecret,
              token: { idToken: 'real-cookie-id-token' },
            });
      const sessionCookies =
        mode === 'enforced'
          ? `${cookieName}=${session}`
          : `${cookieName}.0=${session.slice(0, 100)}; ${cookieName}.1=${session.slice(100)}`;
      const cookie = `${sessionCookies}; waooaw-theme=dark; unrelated=preserve`;
      const post = await POST(
        new NextRequest('https://app.example/api/auth/keycloak-logout', {
          method: 'POST',
          headers: {
            accept: 'application/json',
            origin: 'https://app.example',
            cookie,
          },
          body: JSON.stringify({ command: 'LOCAL_LOGOUT' }),
        })
      );
      expect(post.status).toBe(200);
      const body = await post.json();
      expect(JSON.stringify(body)).not.toContain('real-cookie-id-token');
      if (mode === 'enforced') {
        expect(revokeSession).toHaveBeenCalledWith(
          expect.objectContaining({ sessionFamilyId: 'owned-family' }),
          'CUSTOMER_LOGOUT'
        );
      } else {
        expect(loadSession).not.toHaveBeenCalled();
        expect(post.headers.get('set-cookie')).toContain(`${cookieName}.0=;`);
        expect(post.headers.get('set-cookie')).toContain(`${cookieName}.1=;`);
        expect(post.headers.get('set-cookie')).not.toContain('waooaw-theme=;');
        expect(post.headers.get('set-cookie')).not.toContain('unrelated=;');
      }
      jest.mocked(getToken).mockClear();
      const get = await GET(
        new NextRequest(new URL(body.logoutPath, 'https://app.example'), {
          headers: { cookie: browserCookies(post) },
        })
      );
      expect(get.status).toBe(303);
      const target = new URL(requiredHeader(get, 'location'));
      expect(target.searchParams.get('id_token_hint')).toBe('real-cookie-id-token');
      expect(target.searchParams.get('post_logout_redirect_uri')).toBe('https://app.example/login');
      expect(getToken).not.toHaveBeenCalled();
      expect(get.headers.get('set-cookie')).toContain('waooaw.logout-hint=;');
    }
  );

  it('clears the local session and redirects through Keycloak logout', async () => {
    const request = new NextRequest('https://app.example/api/auth/keycloak-logout', {
      method: 'POST',
      headers: {
        origin: 'https://app.example',
        cookie:
          'next-auth.session-token=local-session; next-auth.session-token.0=chunk; __Host-next-auth.csrf-token=csrf; next-auth.callback-url=%2Fhome; waooaw-theme=dark; unrelated=preserve',
      },
    });

    const response = await POST(request);
    const location = new URL(requiredHeader(response, 'location'));

    expect(response.status).toBe(303);
    expect(location.origin + location.pathname).toBe(
      'https://identity.example/realms/waooaw/protocol/openid-connect/logout'
    );
    expect(location.searchParams.get('id_token_hint')).toBe('server-held-id-token');
    expect(location.searchParams.get('client_id')).toBe('waooaw-web');
    expect(location.searchParams.get('post_logout_redirect_uri')).toBe('https://app.example/login');
    expect(location.searchParams.get('state')).toBe('waooaw-home-after-logout');
    expect(response.headers.get('set-cookie')).toContain('next-auth.session-token=;');
    expect(response.headers.get('set-cookie')).toContain('__Host-next-auth.csrf-token=;');
    expect(response.headers.get('set-cookie')).toContain('next-auth.callback-url=;');
    expect(response.headers.get('set-cookie')).toContain('waooaw-theme=;');
    expect(response.headers.get('set-cookie')).not.toContain('unrelated=;');
    expect(response.headers.get('cache-control')).toBe('no-store');
  });

  it.each(['disabled', 'shadow', 'enforced'] as const)(
    'includes the real %s session ID token in a form logout',
    async (mode) => {
      process.env.WAOOAW_SERVER_SESSION_MODE = mode;
      const actualJwt = jest.requireActual<typeof import('next-auth/jwt')>('next-auth/jwt');
      jest.mocked(getToken).mockImplementation(actualJwt.getToken);
      jest.mocked(loadSession).mockResolvedValue({ idToken: 'form-session-id-token' });
      const session =
        mode === 'enforced'
          ? 'opaque-session-handle'
          : await encode({ secret: testSecret, token: { idToken: 'form-session-id-token' } });
      const cookieName = mode === 'enforced' ? '__Host-waooaw-session' : '__Secure-next-auth.session-token';
      const response = await POST(
        new NextRequest('https://app.example/api/auth/keycloak-logout', {
          method: 'POST',
          headers: { origin: 'https://app.example', cookie: `${cookieName}=${session}` },
        })
      );
      expect(response.status).toBe(303);
      const target = new URL(requiredHeader(response, 'location'));
      expect(target.searchParams.get('id_token_hint')).toBe('form-session-id-token');
      expect(target.searchParams.get('post_logout_redirect_uri')).toBe('https://app.example/login');
      expect(response.headers.get('set-cookie')).toContain(`${cookieName}=;`);
    }
  );

  it('returns an opaque same-origin continuation to JavaScript callers', async () => {
    const response = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        headers: {
          accept: 'application/json',
          origin: 'https://app.example',
          cookie: 'next-auth.session-token=local-session',
        },
      })
    );

    expect(response.status).toBe(200);
    const result = await response.json();
    expect(result.logoutPath).toMatch(/^\/api\/auth\/keycloak-logout\?nonce=[0-9a-f-]+$/);
    expect(JSON.stringify(result)).not.toContain('server-held-id-token');
    expect(response.headers.get('set-cookie')).toContain('waooaw.logout-continuation=');
    expect(response.headers.get('set-cookie')).toContain('HttpOnly');
    expect(response.headers.get('set-cookie')).toContain('Secure');
    expect(response.headers.get('set-cookie')).toContain('SameSite=lax');
    expect(response.headers.get('set-cookie')).toContain('Max-Age=60');
    expect(response.headers.get('set-cookie')).not.toContain('server-held-id-token');
    expect(response.headers.get('set-cookie')).not.toContain('next-auth.session-token=;');
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(getToken).toHaveBeenCalledTimes(1);
  });

  it('revokes before an account-switch continuation and returns to explicit selection', async () => {
    const post = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        body: JSON.stringify({ command: 'ACCOUNT_SWITCH' }),
        headers: {
          accept: 'application/json',
          'content-type': 'application/json',
          origin: 'https://app.example',
        },
      })
    );
    const result = await post.json();
    const nonce = new URL(result.logoutPath, 'https://app.example').searchParams.get('nonce');

    expect(revokeSession).toHaveBeenCalledWith(expect.anything(), 'ACCOUNT_SWITCH');
    const response = await GET(
      new NextRequest(`https://app.example/api/auth/keycloak-logout?nonce=${nonce}`, {
        headers: {
          cookie: browserCookies(post),
        },
      })
    );
    const location = new URL(requiredHeader(response, 'location'));

    expect(location.searchParams.get('post_logout_redirect_uri')).toBe('https://app.example/login');
    expect(location.searchParams.has('state')).toBe(false);
    expect(response.headers.get('set-cookie')).toContain('waooaw.logout-command=;');
  });

  it('clears a stale Keycloak session before resuming an allowlisted registration provider', async () => {
    const post = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        body: JSON.stringify({ command: 'REGISTRATION', provider: 'GOOGLE' }),
        headers: {
          accept: 'application/json',
          'content-type': 'application/json',
          origin: 'https://app.example',
        },
      })
    );
    const result = await post.json();
    const nonce = new URL(result.logoutPath, 'https://app.example').searchParams.get('nonce');
    const setCookie = requiredHeader(post, 'set-cookie');

    expect(setCookie).toContain('waooaw.logout-command=REGISTRATION');
    expect(setCookie).toContain('waooaw.logout-provider=GOOGLE');

    const response = await GET(
      new NextRequest(`https://app.example/api/auth/keycloak-logout?nonce=${nonce}`, {
        headers: {
          cookie: browserCookies(post),
        },
      })
    );
    const location = new URL(requiredHeader(response, 'location'));

    expect(location.searchParams.get('post_logout_redirect_uri')).toBe('https://app.example/login');
    expect(location.searchParams.get('state')).toBe('waooaw-register-after-logout:GOOGLE');
    expect(response.headers.get('set-cookie')).toContain('waooaw.logout-provider=;');
  });

  it('rejects a registration reset without an allowlisted provider', async () => {
    const response = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        body: JSON.stringify({ command: 'REGISTRATION', provider: 'EMAIL' }),
        headers: {
          accept: 'application/json',
          'content-type': 'application/json',
          origin: 'https://app.example',
        },
      })
    );

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      code: 'IDENTITY_ACTION_DENIED',
      title: 'Registration session reset was denied.',
    });
  });

  it('revokes the Web-owned opaque session before returning the logout continuation', async () => {
    jest.mocked(getToken).mockResolvedValue({
      accessToken: 'server-held-access-token',
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 300,
      idToken: 'server-held-id-token',
    });

    const response = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        headers: {
          accept: 'application/json',
          origin: 'https://app.example',
          cookie: '__Host-waooaw-session=opaque-session',
        },
      })
    );

    expect(response.status).toBe(200);
    expect(revokeSession).toHaveBeenCalledWith(
      expect.objectContaining({ accessToken: 'server-held-access-token' }),
      'CUSTOMER_LOGOUT'
    );
  });

  it('does not issue a logout continuation when Web revocation fails', async () => {
    jest.mocked(getToken).mockResolvedValue({
      accessToken: 'server-held-access-token',
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 300,
      idToken: 'server-held-id-token',
    });
    jest.mocked(revokeSession).mockRejectedValueOnce(new Error('session store unavailable'));

    const response = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        headers: {
          accept: 'application/json',
          origin: 'https://app.example',
          cookie: '__Host-waooaw-session=opaque-session',
        },
      })
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      code: 'SESSION_REVOCATION_UNCONFIRMED',
      title: 'Sign out could not be completed.',
    });
    expect(response.headers.get('set-cookie')).toContain('__Host-waooaw-session=;');
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(recordWebIdentitySecurityEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: 'LOGOUT_FAILURE',
        reasonCode: 'SESSION_REVOCATION_UNCONFIRMED',
      })
    );
  });

  it('contains Web session decode failures inside the revocation boundary', async () => {
    jest.mocked(getToken).mockRejectedValueOnce(new Error('session envelope key unavailable'));

    const response = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        body: JSON.stringify({ command: 'ACCOUNT_SWITCH' }),
        headers: {
          accept: 'application/json',
          'content-type': 'application/json',
          origin: 'https://app.example',
          cookie: '__Host-waooaw-session=opaque-session',
        },
      })
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      code: 'SESSION_REVOCATION_UNCONFIRMED',
      title: 'Sign out could not be completed.',
    });
    expect(recordWebIdentitySecurityEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: 'LOGOUT_FAILURE',
        reasonCode: 'SESSION_REVOCATION_UNCONFIRMED',
      })
    );
    expect(revokeSession).not.toHaveBeenCalled();
  });

  it('does not issue a logout continuation when Web revocation is unconfirmed', async () => {
    jest.mocked(getToken).mockResolvedValue({
      accessToken: 'server-held-access-token',
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 300,
      idToken: 'server-held-id-token',
    });
    jest.mocked(revokeSession).mockRejectedValueOnce(new TypeError('session store unavailable'));

    const response = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        headers: {
          accept: 'application/json',
          origin: 'https://app.example',
          cookie: '__Host-waooaw-session=opaque-session',
        },
      })
    );

    expect(response.status).toBe(503);
    expect(response.headers.get('set-cookie')).toContain('__Host-waooaw-session=;');
    expect(recordWebIdentitySecurityEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: 'LOGOUT_FAILURE',
        reasonCode: 'SESSION_REVOCATION_UNCONFIRMED',
      })
    );
  });

  it('redeems the continuation server-side before clearing the session and redirecting', async () => {
    const nonce = '934aca5d-658e-4672-a555-313e88fa49a6';
    const correlationId = '11111111-1111-4111-8111-111111111111';
    const hint = await encode({
      secret: testSecret,
      salt: 'waooaw.logout-hint',
      maxAge: 60,
      token: { nonce, idToken: 'server-held-id-token' },
    });
    jest.mocked(getToken).mockResolvedValue(null);
    const response = await GET(
      new NextRequest(`https://app.example/api/auth/keycloak-logout?nonce=${nonce}`, {
        headers: {
          cookie: `waooaw.logout-continuation=${nonce}; waooaw.logout-hint=${hint}; waooaw.logout-correlation=${correlationId}; next-auth.session-token=local-session`,
        },
      })
    );
    const location = new URL(requiredHeader(response, 'location'));

    expect(response.status).toBe(303);
    expect(location.origin).toBe('https://identity.example');
    expect(location.searchParams.get('id_token_hint')).toBe('server-held-id-token');
    expect(getToken).not.toHaveBeenCalled();
    expect(response.headers.get('set-cookie')).toContain('waooaw.logout-hint=;');
    expect(response.headers.get('set-cookie')).toContain(
      'waooaw.logout-continuation=; Path=/api/auth/keycloak-logout;'
    );
    expect(response.headers.get('set-cookie')).toContain('next-auth.session-token=;');
    expect(recordWebIdentitySecurityEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: 'LOGOUT_REQUEST',
        outcome: 'ATTEMPTED',
        reasonCode: 'IDP_LOGOUT_REDIRECT_STARTED',
      })
    );
    expect(recordWebIdentitySecurityEvent).not.toHaveBeenCalledWith(
      expect.objectContaining({ eventType: 'LOGOUT_COMPLETION' })
    );
  });

  it('carries the ID token across POST revocation and consumes the browser continuation', async () => {
    jest.mocked(revokeSession).mockImplementationOnce(async () => {
      jest.mocked(getToken).mockResolvedValue(null);
    });
    const post = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        headers: { accept: 'application/json', origin: 'https://app.example' },
      })
    );
    const { logoutPath } = await post.json();
    const redirected = await GET(
      new NextRequest(new URL(logoutPath, 'https://app.example'), {
        headers: { cookie: browserCookies(post) },
      })
    );
    expect(new URL(requiredHeader(redirected, 'location')).searchParams.get('id_token_hint')).toBe(
      'server-held-id-token'
    );
    expect(revokeSession).toHaveBeenCalledTimes(1);
    expect(getToken).toHaveBeenCalledTimes(1);
    const replay = await GET(
      new NextRequest(new URL(logoutPath, 'https://app.example'), {
        headers: { cookie: browserCookies(redirected) },
      })
    );
    expect(replay.status).toBe(403);
  });

  it.each(['missing', 'expired', 'tampered', 'wrong-nonce'])('rejects a %s hint safely', async (kind) => {
    const nonce = crypto.randomUUID();
    const hint =
      kind === 'missing'
        ? ''
        : kind === 'tampered'
          ? 'invalid'
          : await encode({
              secret: testSecret,
              salt: 'waooaw.logout-hint',
              maxAge: kind === 'expired' ? -1 : 60,
              token: {
                nonce: kind === 'wrong-nonce' ? 'other' : nonce,
                idToken: 'secret-id-token',
              },
            });
    const response = await GET(
      new NextRequest(`https://app.example/api/auth/keycloak-logout?nonce=${nonce}`, {
        headers: {
          cookie: `waooaw.logout-continuation=${nonce}; waooaw.logout-hint=${hint}`,
        },
      })
    );
    expect(response.status).toBe(403);
    expect(response.headers.get('location')).toBeNull();
    expect(response.headers.get('set-cookie')).toContain('waooaw.logout-hint=;');
    expect(getToken).not.toHaveBeenCalled();
  });

  it('rejects an invalid logout continuation without reading the session', async () => {
    const response = await GET(
      new NextRequest('https://app.example/api/auth/keycloak-logout?nonce=forged', {
        headers: { cookie: 'waooaw.logout-continuation=expected' },
      })
    );

    expect(response.status).toBe(403);
    expect(getToken).not.toHaveBeenCalled();
  });

  it('rejects a cross-origin logout submission', async () => {
    const response = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        headers: { origin: 'https://attacker.example' },
      })
    );

    expect(response.status).toBe(403);
    expect(getToken).not.toHaveBeenCalled();
  });

  it('accepts a browser form submission with same-origin fetch metadata when Origin is omitted', async () => {
    const response = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
        headers: {
          'sec-fetch-site': 'same-origin',
          cookie: '__Secure-next-auth.session-token.0=first; __Secure-next-auth.session-token.1=second',
        },
      })
    );

    expect(response.status).toBe(303);
    expect(response.headers.get('set-cookie')).toContain('__Secure-next-auth.session-token.0=;');
    expect(response.headers.get('set-cookie')).toContain('__Secure-next-auth.session-token.1=;');
  });

  it('accepts a same-origin logout through a trusted reverse proxy', async () => {
    const response = await POST(
      new NextRequest('https://0.0.0.0:3000/api/auth/keycloak-logout', {
        method: 'POST',
        headers: {
          accept: 'application/json',
          'content-type': 'application/json',
          origin: 'http://localhost:3100',
          referer: 'https://app.example/home',
          'sec-fetch-site': 'same-origin',
          'x-forwarded-host': 'app.example',
          'x-forwarded-proto': 'https',
        },
        body: JSON.stringify({ command: 'ACCOUNT_SWITCH' }),
      })
    );

    expect(response.status).toBe(200);
  });

  it('rejects a logout submission without same-origin provenance', async () => {
    const response = await POST(
      new NextRequest('https://app.example/api/auth/keycloak-logout', {
        method: 'POST',
      })
    );

    expect(response.status).toBe(403);
    expect(getToken).not.toHaveBeenCalled();
  });

  it('does not trust a forged request host for the post-logout target', async () => {
    const response = await POST(
      new NextRequest('https://attacker.example/api/auth/keycloak-logout', {
        method: 'POST',
        headers: { origin: 'https://app.example' },
      })
    );

    expect(new URL(requiredHeader(response, 'location')).searchParams.get('post_logout_redirect_uri')).toBe(
      'https://app.example/login'
    );
  });
});
