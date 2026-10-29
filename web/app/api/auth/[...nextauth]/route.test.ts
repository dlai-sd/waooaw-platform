/** @jest-environment node */

jest.mock('next-auth', () => ({
  __esModule: true,
  ...(() => {
    const mockHandler = jest.fn();
    return { default: () => mockHandler, mockHandler };
  })(),
}));
jest.mock('@/lib/auth', () => ({ authOptions: {} }));
jest.mock('@/lib/journey-telemetry', () => ({
  withJourneyTrace: (_name: string, operation: () => unknown) => operation(),
}));
jest.mock('@/lib/web-session-store', () => ({
  createOidcTransaction: jest.fn(),
  consumeOidcTransaction: jest.fn(),
}));
jest.mock('@/lib/auth-abuse-limiter', () => ({
  enforceAuthAbuse: jest.fn(),
}));

import { enforceAuthAbuse } from '@/lib/auth-abuse-limiter';
import { consumeOidcTransaction, createOidcTransaction } from '@/lib/web-session-store';
import { NextRequest } from 'next/server';
import { GET, POST } from './route';

const mockNextAuthHandler = jest.requireMock('next-auth').mockHandler as jest.Mock;
const state = 'one-time-oidc-state';
const protocolCookies = {
  '__Secure-next-auth.state': 'state-cookie',
  '__Secure-next-auth.nonce': 'nonce-cookie',
  '__Secure-next-auth.pkce.code_verifier': 'pkce-cookie',
};

function initiationResponse() {
  const headers = new Headers({ 'content-type': 'application/json' });
  for (const [name, value] of Object.entries(protocolCookies))
    headers.append('set-cookie', `${name}=${value}; Path=/; HttpOnly`);
  return new Response(
    JSON.stringify({
      url: `https://identity.example/realms/waooaw/protocol/openid-connect/auth?state=${state}`,
    }),
    { headers }
  );
}

describe('NextAuth OIDC transaction boundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXTAUTH_URL = 'https://app.example';
    jest.mocked(enforceAuthAbuse).mockResolvedValue(null);
  });

  afterEach(() => jest.restoreAllMocks());

  it('fails closed before provider initiation when the limiter is unavailable', async () => {
    jest.mocked(enforceAuthAbuse).mockResolvedValue(new Response(null, { status: 503 }) as never);

    const response = await POST(
      new NextRequest('https://app.example/api/auth/signin/keycloak-google', {
        method: 'POST',
      })
    );

    expect(response.status).toBe(503);
    expect(mockNextAuthHandler).not.toHaveBeenCalled();
    expect(createOidcTransaction).not.toHaveBeenCalled();
  });

  it('durably binds intent, protocol cookies, provider, and browser before redirect', async () => {
    mockNextAuthHandler.mockResolvedValue(initiationResponse());
    const body = new URLSearchParams({
      callbackUrl: '/login?returnTo=/settings',
      waooawIntent: 'LOGIN',
    });

    const response = await POST(
      new NextRequest('https://app.example/api/auth/signin/keycloak-google', {
        method: 'POST',
        body,
        headers: {
          'content-type': 'application/x-www-form-urlencoded',
        },
      })
    );

    expect(response.status).toBe(200);
    expect(createOidcTransaction).toHaveBeenCalledWith(state, expect.any(String), 'GOOGLE', {
      state,
      intent: 'LOGIN',
      callbackPath: '/login?returnTo=%2Fsettings',
      protocolCookies,
    });
    expect(response.headers.get('set-cookie')).toContain('__Host-waooaw-oidc-browser=');
    expect(response.headers.get('set-cookie')).toContain('Path=/;');
    expect(response.headers.get('set-cookie')).toContain('Secure');
  });

  it('returns no provider redirect when durable reservation is unavailable', async () => {
    mockNextAuthHandler.mockResolvedValue(initiationResponse());
    jest.mocked(createOidcTransaction).mockRejectedValueOnce(new Error('session store unavailable'));
    jest.spyOn(console, 'error').mockImplementation(() => {});

    const response = await POST(
      new NextRequest('https://app.example/api/auth/signin/keycloak-google', {
        method: 'POST',
        body: new URLSearchParams({
          callbackUrl: '/login?returnTo=/home',
          waooawIntent: 'LOGIN',
        }),
        headers: {
          'content-type': 'application/x-www-form-urlencoded',
        },
      })
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      code: 'IDENTITY_DEPENDENCY_UNAVAILABLE',
      correlationId: expect.stringMatching(/^[0-9a-f-]{36}$/),
    });
    expect(response.headers.get('set-cookie')).toBeNull();
  });

  it('logs the safe SQLSTATE of a rejected reservation without payload, message or parameters', async () => {
    mockNextAuthHandler.mockResolvedValue(initiationResponse());
    // Shape of the minified postgres.js PostgresError seen in Demo (`cause: 'k'`).
    const rejection = Object.assign(
      new Error('new row violates row-level security policy for table "oidc_transactions"'),
      {
        name: 'k',
        code: '42501',
        severity_local: 'ERROR',
        severity: 'ERROR',
        schema_name: 'web_session',
        table_name: 'oidc_transactions',
        routine: 'ExecWithCheckOptions',
        detail: `Failing row contains (${state}, nonce-cookie)`,
        where: 'SQL function "create_oidc_transaction" statement 1',
        parameters: [state, 'pkce-cookie'],
        query: 'SELECT web_session.create_oidc_transaction($1)',
      }
    );
    jest.mocked(createOidcTransaction).mockRejectedValueOnce(rejection);
    const logged = jest.spyOn(console, 'error').mockImplementation(() => {});

    const response = await POST(
      new NextRequest('https://app.example/api/auth/signin/keycloak-google', {
        method: 'POST',
        body: new URLSearchParams({ callbackUrl: '/home', waooawIntent: 'LOGIN' }),
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
      })
    );

    expect(response.status).toBe(503);
    const { correlationId } = (await response.json()) as { correlationId: string };
    expect(logged).toHaveBeenCalledTimes(1);
    expect(JSON.parse(String(logged.mock.calls[0][0]))).toEqual({
      level: 'error',
      event: 'identity.oidc_transaction.reserve_failed',
      provider: 'GOOGLE',
      correlationId,
      errorType: 'Error',
      errorClass: 'database',
      code: '42501',
      severity: 'ERROR',
      schema: 'web_session',
      table: 'oidc_transactions',
      routine: 'ExecWithCheckOptions',
    });
    const serialized = JSON.stringify(logged.mock.calls);
    for (const secret of [state, 'nonce-cookie', 'pkce-cookie', 'row-level security', 'SELECT'])
      expect(serialized).not.toContain(secret);
  });

  it('adds a redacted message and stack when WAOOAW_DIAGNOSTIC_DETAIL=stack', async () => {
    process.env.WAOOAW_DIAGNOSTIC_DETAIL = 'stack';
    mockNextAuthHandler.mockResolvedValue(initiationResponse());
    const rejection = Object.assign(
      new Error(`new row violates row-level security policy for table "oidc_transactions" state=${state}`),
      {
        code: '42501',
        detail: `Failing row contains (${state}, nonce-cookie)`,
        parameters: [state, 'pkce-cookie'],
        query: 'SELECT web_session.create_oidc_transaction($1)',
      }
    );
    jest.mocked(createOidcTransaction).mockRejectedValueOnce(rejection);
    const logged = jest.spyOn(console, 'error').mockImplementation(() => {});

    try {
      await POST(
        new NextRequest('https://app.example/api/auth/signin/keycloak-google', {
          method: 'POST',
          body: new URLSearchParams({ callbackUrl: '/home', waooawIntent: 'LOGIN' }),
          headers: { 'content-type': 'application/x-www-form-urlencoded' },
        })
      );
    } finally {
      Reflect.deleteProperty(process.env, 'WAOOAW_DIAGNOSTIC_DETAIL');
    }

    const record = JSON.parse(String(logged.mock.calls[0][0])) as Record<string, string>;
    expect(record.code).toBe('42501');
    expect(record.message).toBe(
      'new row violates row-level security policy for table "oidc_transactions" state=[redacted]'
    );
    expect(record.stack).toMatch(/^at /);
    const serialized = JSON.stringify(logged.mock.calls);
    for (const secret of [state, 'nonce-cookie', 'pkce-cookie', 'SELECT']) expect(serialized).not.toContain(secret);
  });

  it('logs why provider-start produced no redirect instead of failing silently', async () => {
    mockNextAuthHandler.mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    const logged = jest.spyOn(console, 'error').mockImplementation(() => {});

    const response = await POST(
      new NextRequest('https://app.example/api/auth/signin/keycloak-facebook', {
        method: 'POST',
        body: new URLSearchParams({ callbackUrl: '/home', waooawIntent: 'LOGIN' }),
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
      })
    );

    expect(response.status).toBe(503);
    expect(JSON.parse(String(logged.mock.calls[0][0]))).toMatchObject({
      event: 'identity.provider_start.redirect_missing',
      provider: 'FACEBOOK',
      upstreamStatus: 200,
      errorType: 'none',
    });
  });

  it('classifies non-database reservation failures without echoing their message', async () => {
    mockNextAuthHandler.mockResolvedValue(initiationResponse());
    jest.mocked(createOidcTransaction).mockRejectedValueOnce(new Error('SESSION_TOKEN_ENVELOPE_KEYS secret=abc'));
    const logged = jest.spyOn(console, 'error').mockImplementation(() => {});

    await POST(
      new NextRequest('https://app.example/api/auth/signin/keycloak-google', {
        method: 'POST',
        body: new URLSearchParams({ callbackUrl: '/home', waooawIntent: 'LOGIN' }),
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
      })
    );

    const record = JSON.parse(String(logged.mock.calls[0][0])) as Record<string, string>;
    expect(record).toMatchObject({ event: 'identity.oidc_transaction.reserve_failed', errorType: 'Error' });
    expect(record.errorClass).toBeUndefined();
    expect(JSON.stringify(logged.mock.calls)).not.toContain('secret=abc');
  });

  it('consumes the transaction before accepting the callback and enforces its route', async () => {
    jest.mocked(consumeOidcTransaction).mockResolvedValue({
      state,
      providerClass: 'GOOGLE',
      intent: 'LOGIN',
      callbackPath: '/login?returnTo=%2Fsettings',
      protocolCookies,
    });
    mockNextAuthHandler.mockResolvedValue(Response.redirect('https://app.example/login?returnTo=/home', 303));
    const cookie = [
      '__Host-waooaw-oidc-browser=browser-binding',
      ...Object.entries(protocolCookies).map(([name, value]) => `${name}=${value}`),
    ].join('; ');

    const response = await GET(
      new NextRequest(`https://app.example/api/auth/callback/keycloak-google?state=${state}&code=opaque`, {
        headers: { cookie },
      })
    );

    expect(consumeOidcTransaction).toHaveBeenCalledWith(state, 'browser-binding');
    expect(mockNextAuthHandler).toHaveBeenCalledTimes(1);
    expect(response.headers.get('location')).toBe('https://app.example/login?returnTo=%2Fsettings');
    expect(response.headers.get('set-cookie')).toContain('__Host-waooaw-oidc-browser=;');
    expect(response.headers.get('set-cookie')).toContain('Path=/;');
  });

  it('denies a consumed or mismatched callback before NextAuth creates a session', async () => {
    jest.mocked(consumeOidcTransaction).mockResolvedValue(null);

    const response = await GET(
      new NextRequest(`https://app.example/api/auth/callback/keycloak-google?state=${state}&code=opaque`, {
        headers: {
          cookie: '__Host-waooaw-oidc-browser=browser-binding; __Secure-next-auth.state=state-cookie',
        },
      })
    );

    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toContain('/auth/error?error=OAuthCallback');
    expect(mockNextAuthHandler).not.toHaveBeenCalled();
  });
});
