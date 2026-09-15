// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-03
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import type { Session } from 'next-auth';
import { activeAccessToken, authOptions, hasFounderClaim, keycloakClientConfig, projectSession } from './auth';

describe('Founder claim parsing', () => {
  it('accepts only an explicit Founder claim or realm role', () => {
    expect(hasFounderClaim({ founder: true })).toBe(true);
    expect(hasFounderClaim({ realm_access: { roles: ['customer', 'founder'] } })).toBe(true);
    expect(hasFounderClaim({ founder: false, realm_access: { roles: ['customer'] } })).toBe(false);
    expect(hasFounderClaim({ founder: 'true' })).toBe(false);
    expect(hasFounderClaim(undefined)).toBe(false);
  });
});

describe('Browser session projection', () => {
  afterEach(() => {
    jest.restoreAllMocks();
    Reflect.deleteProperty(globalThis, 'fetch');
  });

  it('reports authentication without exposing the Keycloak bearer token', () => {
    const session = projectSession(
      { expires: '2099-01-01', user: {} } as Session,
      { accessToken: 'secret-bearer-token', accessTokenExpiresAt: 101, founder: false },
      100,
    );
    expect(session.authenticated).toBe(true);
    expect(session).not.toHaveProperty('accessToken');
    expect(JSON.stringify(session)).not.toContain('secret-bearer-token');
  });

  it.each([
    ['expired', { accessToken: 'secret-bearer-token', accessTokenExpiresAt: 100, founder: true }],
    ['missing expiry', { accessToken: 'secret-bearer-token', founder: true }],
    ['missing token', { accessTokenExpiresAt: 101, founder: true }],
  ])('fails closed for %s token state', (_scenario, token) => {
    expect(activeAccessToken(token, 100)).toBeUndefined();
    const session = projectSession({ expires: '2099-01-01', user: {} } as Session, token, 100);
    expect(session.authenticated).toBe(false);
    expect(session.founder).toBe(false);
  });

  it('records the Keycloak bearer expiry during the OAuth callback', async () => {
    const jwt = authOptions.callbacks?.jwt;
    const expiresAt = Math.floor(Date.now() / 1000) + 60;
    expect(jwt).toBeDefined();

    const token = await jwt!({
      token: {},
      account: {
        access_token: 'secret-bearer-token', expires_at: expiresAt,
        refresh_token: 'server-held-refresh-token', id_token: 'server-held-id-token',
      },
      profile: { realm_access: { roles: ['founder'] } },
    } as never);

    expect(token).toMatchObject({
      accessToken: 'secret-bearer-token',
      accessTokenExpiresAt: expiresAt,
      refreshToken: 'server-held-refresh-token',
      idToken: 'server-held-id-token',
      founder: true,
    });
  });

  it('purges expired bearer and Founder state during session evaluation', async () => {
    const jwt = authOptions.callbacks?.jwt;
    expect(jwt).toBeDefined();

    const token = await jwt!({
      token: { accessToken: 'expired-bearer-token', accessTokenExpiresAt: 1, founder: true },
      account: null,
    } as never);

    expect(token).not.toHaveProperty('accessToken');
    expect(token).not.toHaveProperty('accessTokenExpiresAt');
    expect(token.founder).toBe(false);
  });

  it('refreshes an expired bearer without exposing the refresh token to the browser session', async () => {
    jest.spyOn(Date, 'now').mockReturnValue(100_000);
    const refresh = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: 'renewed-bearer-token',
        expires_in: 300,
        refresh_token: 'rotated-refresh-token',
        id_token: 'renewed-id-token',
      }),
    });
    Object.defineProperty(globalThis, 'fetch', { configurable: true, value: refresh });
    const jwt = authOptions.callbacks?.jwt;

    const token = await jwt!({
      token: {
        accessToken: 'expired-bearer-token', accessTokenExpiresAt: 1,
        refreshToken: 'server-held-refresh-token', founder: false,
      },
      account: null,
    } as never);

    expect(refresh).toHaveBeenCalledWith(
      'http://localhost:8080/realms/waooaw/protocol/openid-connect/token',
      expect.objectContaining({ method: 'POST', cache: 'no-store' }),
    );
    const request = refresh.mock.calls[0][1] as RequestInit;
    expect(String(request.body)).toBe(
      'grant_type=refresh_token&refresh_token=server-held-refresh-token&client_id=waooaw-web&client_secret=local-development-only',
    );
    expect(token).toMatchObject({
      accessToken: 'renewed-bearer-token',
      accessTokenExpiresAt: 400,
      refreshToken: 'rotated-refresh-token',
      idToken: 'renewed-id-token',
    });
    const session = projectSession({ expires: '2099-01-01', user: {} } as Session, token, 100);
    expect(session.authenticated).toBe(true);
    expect(JSON.stringify(session)).not.toContain('rotated-refresh-token');
  });

  it('purges all authentication authority when Keycloak rejects refresh', async () => {
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: jest.fn().mockResolvedValue({ ok: false }),
    });
    const jwt = authOptions.callbacks?.jwt;

    const token = await jwt!({
      token: {
        accessToken: 'expired-bearer-token', accessTokenExpiresAt: 1,
        refreshToken: 'rejected-refresh-token', founder: true,
      },
      account: null,
    } as never);

    expect(token).not.toHaveProperty('accessToken');
    expect(token).not.toHaveProperty('accessTokenExpiresAt');
    expect(token).not.toHaveProperty('refreshToken');
    expect(token.founder).toBe(false);
  });
});

describe('Keycloak broker configuration', () => {
  it('keeps broker aliases in server-owned provider configuration', () => {
    const providers = authOptions.providers as Array<{ id: string; authorization?: { params?: Record<string, string> } }>;

    expect(providers.find((provider) => provider.id === 'keycloak-google')?.authorization?.params).toEqual({
      scope: 'openid profile email', kc_idp_hint: 'google',
    });
    expect(providers.find((provider) => provider.id === 'keycloak-facebook')?.authorization?.params).toEqual({
      scope: 'openid profile email', kc_idp_hint: 'facebook',
    });
    expect(providers.find((provider) => provider.id === 'keycloak-apple')?.authorization?.params).toEqual({
      scope: 'openid profile email', kc_idp_hint: 'apple',
    });
  });

  it('keeps the confidential web client as the default runtime mode', () => {
    expect(keycloakClientConfig({})).toEqual({
      clientId: 'waooaw-web',
      clientSecret: 'local-development-only',
      issuer: 'http://localhost:8080/realms/waooaw',
    });
  });

  it('requires an explicit opt-in for a secretless public PKCE client', () => {
    expect(keycloakClientConfig({
      KEYCLOAK_PUBLIC_CLIENT: 'true',
      KEYCLOAK_CLIENT_ID: 'waooaw-web-preview',
      KEYCLOAK_CLIENT_SECRET: 'must-not-be-used',
      KEYCLOAK_ISSUER: 'https://demo.example/realms/waooaw',
    })).toEqual({
      clientId: 'waooaw-web-preview',
      clientSecret: '',
      issuer: 'https://demo.example/realms/waooaw',
      client: { token_endpoint_auth_method: 'none' },
    });
  });
});