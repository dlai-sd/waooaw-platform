// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-03
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import type { Session } from 'next-auth';
import {
  activeAccessToken,
  authOptions,
  bindPreviewDeployment,
  hasFounderClaim,
  keycloakClientConfig,
  previewSessionMaxAge,
  projectSession,
} from './auth';
import { persistWebIdentitySecurityEvent, recordWebIdentitySecurityEvent } from './identity-security-events';
import { acquireRefreshLease, completeRefresh, createSession, loadSession } from './web-session-store';

jest.mock('next-auth/jwt', () => ({
  encode: jest.fn(),
  decode: jest.fn(),
}));
jest.mock('./identity-security-events', () => ({
  persistWebIdentitySecurityEvent: jest.fn(),
  recordWebIdentitySecurityEvent: jest.fn(),
}));
jest.mock('./web-session-store', () => ({
  acquireRefreshLease: jest.fn(),
  completeRefresh: jest.fn(),
  createSession: jest.fn(),
  loadSession: jest.fn(),
  revokeSession: jest.fn(),
}));

beforeEach(() => {
  jest.mocked(persistWebIdentitySecurityEvent).mockReset().mockResolvedValue(true);
  jest.mocked(recordWebIdentitySecurityEvent).mockReset().mockResolvedValue();
  jest.mocked(acquireRefreshLease).mockReset().mockResolvedValue('00000000-0000-4000-8000-000000000001');
  jest.mocked(completeRefresh).mockReset().mockResolvedValue(true);
  jest.mocked(loadSession).mockReset();
  jest
    .mocked(createSession)
    .mockReset()
    .mockImplementation(async (token) => ({ ...token, sessionHandle: 'h'.repeat(43) }));
});

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
      100
    );
    expect(session.authenticated).toBe(true);
    expect(session).not.toHaveProperty('accessToken');
    expect(JSON.stringify(session)).not.toContain('secret-bearer-token');
  });

  it('encodes only the opaque random handle into the browser cookie', async () => {
    const handle = 'h'.repeat(43);
    const encoded = await authOptions.jwt?.encode?.({
      token: {
        sessionHandle: handle,
        accessToken: 'secret-bearer-token',
        refreshToken: 'secret-refresh-token',
      },
      secret: 'test-secret',
      maxAge: 3600,
    });
    expect(encoded).toBe(handle);
    expect(encoded).not.toContain('secret');

    jest.mocked(loadSession).mockResolvedValueOnce({ sessionHandle: handle });
    await expect(authOptions.jwt?.decode?.({ token: handle, secret: 'test-secret' })).resolves.toEqual({
      sessionHandle: handle,
    });
  });

  it('uses a bounded one-hour lifetime for deployment-bound preview sessions', () => {
    expect(
      previewSessionMaxAge({
        AUTH_PREVIEW_DEPLOYMENT_ID: 'deployment-a',
        AUTH_PREVIEW_SESSION_MAX_AGE_SECONDS: '3600',
      })
    ).toBe(3600);
    expect(previewSessionMaxAge({})).toBeUndefined();
  });

  it('purges authentication authority from a cookie issued by another deployment', () => {
    const token = bindPreviewDeployment(
      {
        accessToken: 'old-bearer',
        accessTokenExpiresAt: 999,
        refreshToken: 'old-refresh',
        founder: true,
        previewDeploymentId: 'deployment-a',
      },
      false,
      'deployment-b'
    );

    expect(token).not.toHaveProperty('accessToken');
    expect(token).not.toHaveProperty('refreshToken');
    expect(token.founder).toBe(false);
    expect(token.previewDeploymentId).toBe('deployment-b');
  });

  it('binds a newly authenticated token to the active deployment', () => {
    expect(bindPreviewDeployment({ accessToken: 'new-bearer' }, true, 'deployment-b')).toMatchObject({
      accessToken: 'new-bearer',
      previewDeploymentId: 'deployment-b',
    });
  });

  it.each([
    ['expired', { accessToken: 'secret-bearer-token', accessTokenExpiresAt: 100, founder: true }],
    ['missing expiry', { accessToken: 'secret-bearer-token', founder: true }],
    ['missing token', { accessTokenExpiresAt: 101, founder: true }],
    ['blank token', { accessToken: '   ', accessTokenExpiresAt: 101, founder: true }],
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
    if (!jwt) throw new Error('JWT callback is required');

    const token = await jwt({
      token: {},
      account: {
        access_token: 'secret-bearer-token',
        expires_at: expiresAt,
        refresh_token: 'server-held-refresh-token',
        id_token: 'server-held-id-token',
      },
      profile: {
        iss: 'https://identity.example/realms/waooaw',
        sub: 'customer-subject',
        realm_access: { roles: ['founder'] },
      },
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
    if (!jwt) throw new Error('JWT callback is required');

    const token = await jwt({
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
    if (!jwt) throw new Error('JWT callback is required');

    const token = await jwt({
      token: {
        accessToken: 'expired-bearer-token',
        accessTokenExpiresAt: 1,
        refreshToken: 'server-held-refresh-token',
        founder: false,
      },
      account: null,
    } as never);

    expect(refresh).toHaveBeenCalledWith(
      'http://localhost:8080/realms/waooaw/protocol/openid-connect/token',
      expect.objectContaining({ method: 'POST', cache: 'no-store' })
    );
    const request = refresh.mock.calls[0][1] as RequestInit;
    expect(String(request.body)).toBe(
      'grant_type=refresh_token&refresh_token=server-held-refresh-token&client_id=waooaw-web&client_secret=local-development-only'
    );
    expect(token).toMatchObject({
      accessToken: 'renewed-bearer-token',
      accessTokenExpiresAt: 400,
      refreshToken: 'rotated-refresh-token',
      idToken: 'renewed-id-token',
    });
    expect(persistWebIdentitySecurityEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: 'REFRESH_SUCCESS',
        reasonCode: 'TOKEN_ROTATED',
      })
    );
    const session = projectSession({ expires: '2099-01-01', user: {} } as Session, token, 100);
    expect(session.authenticated).toBe(true);
    expect(JSON.stringify(session)).not.toContain('rotated-refresh-token');
  });

  it('makes refresh contenders consume the committed winner without another provider call', async () => {
    jest.mocked(acquireRefreshLease).mockResolvedValueOnce(null);
    jest.mocked(loadSession).mockResolvedValueOnce({
      sessionHandle: 'h'.repeat(43),
      accessToken: 'winner-access-token',
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 300,
      refreshVersion: 4,
    });
    const providerCall = jest.fn();
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: providerCall,
    });
    const jwt = authOptions.callbacks?.jwt;
    if (!jwt) throw new Error('JWT callback is required');

    const token = await jwt({
      token: {
        sessionHandle: 'h'.repeat(43),
        accessToken: 'expired',
        accessTokenExpiresAt: 1,
        refreshToken: 'loser-refresh-token',
      },
      account: null,
    } as never);

    expect(token).toMatchObject({
      accessToken: 'winner-access-token',
      refreshVersion: 4,
    });
    expect(providerCall).not.toHaveBeenCalled();
  });

  it('fails closed when the session store cannot arbitrate refresh', async () => {
    jest.mocked(acquireRefreshLease).mockRejectedValueOnce(new Error('session database unavailable'));
    const providerCall = jest.fn();
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: providerCall,
    });
    const jwt = authOptions.callbacks?.jwt;
    if (!jwt) throw new Error('JWT callback is required');

    const token = await jwt({
      token: {
        sessionHandle: 'h'.repeat(43),
        accessToken: 'expired',
        accessTokenExpiresAt: 1,
        refreshToken: 'server-held-refresh-token',
        founder: true,
      },
      account: null,
    } as never);

    expect(token).not.toHaveProperty('accessToken');
    expect(token).not.toHaveProperty('refreshToken');
    expect(token.founder).toBe(false);
    expect(providerCall).not.toHaveBeenCalled();
    expect(recordWebIdentitySecurityEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: 'REFRESH_FAILURE',
        reasonCode: 'SESSION_STORE_UNAVAILABLE',
      })
    );
  });

  it('purges refreshed authority when the required success event cannot be persisted', async () => {
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ access_token: 'unrecorded-bearer', expires_in: 300 }),
      }),
    });
    jest.mocked(persistWebIdentitySecurityEvent).mockRejectedValueOnce(new Error('event store unavailable'));
    const jwt = authOptions.callbacks?.jwt;
    if (!jwt) throw new Error('JWT callback is required');

    const token = await jwt({
      token: { accessToken: 'expired', accessTokenExpiresAt: 1, refreshToken: 'refresh', founder: true },
      account: null,
    } as never);

    expect(token).not.toHaveProperty('accessToken');
    expect(token).not.toHaveProperty('refreshToken');
    expect(token.founder).toBe(false);
    expect(recordWebIdentitySecurityEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: 'REFRESH_FAILURE',
        reasonCode: 'EVENT_PERSISTENCE_UNAVAILABLE',
      })
    );
  });

  it('purges all authentication authority when Keycloak rejects refresh', async () => {
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: jest.fn().mockResolvedValue({ ok: false }),
    });
    const jwt = authOptions.callbacks?.jwt;
    if (!jwt) throw new Error('JWT callback is required');

    const token = await jwt({
      token: {
        accessToken: 'expired-bearer-token',
        accessTokenExpiresAt: 1,
        refreshToken: 'rejected-refresh-token',
        founder: true,
      },
      account: null,
    } as never);

    expect(token).not.toHaveProperty('accessToken');
    expect(token).not.toHaveProperty('accessTokenExpiresAt');
    expect(token).not.toHaveProperty('refreshToken');
    expect(token.founder).toBe(false);
  });

  it('purges authentication authority when Keycloak returns a blank access token', async () => {
    Object.defineProperty(globalThis, 'fetch', {
      configurable: true,
      value: jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ access_token: '  ', expires_in: 300 }),
      }),
    });
    const jwt = authOptions.callbacks?.jwt;
    if (!jwt) throw new Error('JWT callback is required');

    const token = await jwt({
      token: { accessToken: 'expired', accessTokenExpiresAt: 1, refreshToken: 'refresh', founder: true },
      account: null,
    } as never);

    expect(token).not.toHaveProperty('accessToken');
    expect(token).not.toHaveProperty('refreshToken');
    expect(token.founder).toBe(false);
  });
});

describe('Keycloak broker configuration', () => {
  it('keeps broker aliases in server-owned provider configuration', () => {
    const providers = authOptions.providers as Array<{
      id: string;
      authorization?: { params?: Record<string, string> };
    }>;

    expect(providers.find((provider) => provider.id === 'keycloak-google')?.authorization?.params).toEqual({
      scope: 'openid profile email',
      kc_idp_hint: 'google',
      prompt: 'select_account',
      max_age: '0',
    });
    expect(providers.find((provider) => provider.id === 'keycloak-facebook')?.authorization?.params).toEqual({
      scope: 'openid profile email',
      kc_idp_hint: 'facebook',
    });
    expect(providers.find((provider) => provider.id === 'keycloak-apple')?.authorization?.params).toEqual({
      scope: 'openid profile email',
      kc_idp_hint: 'apple',
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
    expect(
      keycloakClientConfig({
        KEYCLOAK_PUBLIC_CLIENT: 'true',
        KEYCLOAK_CLIENT_ID: 'waooaw-web-preview',
        KEYCLOAK_CLIENT_SECRET: 'must-not-be-used',
        KEYCLOAK_ISSUER: 'https://demo.example/realms/waooaw',
      })
    ).toEqual({
      clientId: 'waooaw-web-preview',
      clientSecret: '',
      issuer: 'https://demo.example/realms/waooaw',
      client: { token_endpoint_auth_method: 'none' },
    });
  });

  it('rejects unpinned or insecure production issuers', () => {
    expect(() =>
      keycloakClientConfig({
        NODE_ENV: 'production',
        KEYCLOAK_ISSUER: 'http://identity.example/realms/waooaw',
      })
    ).toThrow('Pinned Keycloak issuer configuration is invalid');
    expect(() =>
      keycloakClientConfig({
        NODE_ENV: 'production',
        KEYCLOAK_ISSUER: 'https://identity.example/realms/other',
        KEYCLOAK_EXPECTED_ISSUER: 'https://identity.example/realms/waooaw',
      })
    ).toThrow('Pinned Keycloak issuer configuration is invalid');
  });
});
