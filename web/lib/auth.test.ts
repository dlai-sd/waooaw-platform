// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-03
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import type { Session } from 'next-auth';
import { authOptions, hasFounderClaim, keycloakClientConfig, projectSession } from './auth';

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
  it('reports authentication without exposing the Keycloak bearer token', () => {
    const session = projectSession({ expires: '2099-01-01', user: {} } as Session, { accessToken: 'secret-bearer-token', founder: false });
    expect(session.authenticated).toBe(true);
    expect(session).not.toHaveProperty('accessToken');
    expect(JSON.stringify(session)).not.toContain('secret-bearer-token');
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