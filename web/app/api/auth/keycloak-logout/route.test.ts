/** @jest-environment node */

jest.mock('next-auth/jwt', () => ({ getToken: jest.fn() }));

import { getToken } from 'next-auth/jwt';
import { NextRequest } from 'next/server';
import { GET, POST } from './route';

function requiredHeader(response: Response, name: string): string {
  const value = response.headers.get(name);
  expect(value).not.toBeNull();
  return value ?? '';
}

describe('Keycloak logout route', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.KEYCLOAK_ISSUER = 'https://identity.example/realms/waooaw';
    process.env.KEYCLOAK_CLIENT_ID = 'waooaw-web';
    process.env.NEXTAUTH_URL = 'https://app.example';
    jest.mocked(getToken).mockResolvedValue({ idToken: 'server-held-id-token' });
  });

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
    expect(location.searchParams.get('post_logout_redirect_uri')).toBe('https://app.example/');
    expect(response.headers.get('set-cookie')).toContain('next-auth.session-token=;');
    expect(response.headers.get('set-cookie')).toContain('__Host-next-auth.csrf-token=;');
    expect(response.headers.get('set-cookie')).toContain('next-auth.callback-url=;');
    expect(response.headers.get('set-cookie')).toContain('waooaw-theme=;');
    expect(response.headers.get('set-cookie')).not.toContain('unrelated=;');
    expect(response.headers.get('cache-control')).toBe('no-store');
  });

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
    expect(response.headers.get('set-cookie')).not.toContain('next-auth.session-token=;');
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(getToken).not.toHaveBeenCalled();
  });

  it('redeems the continuation server-side before clearing the session and redirecting', async () => {
    const nonce = '934aca5d-658e-4672-a555-313e88fa49a6';
    const response = await GET(
      new NextRequest(`https://app.example/api/auth/keycloak-logout?nonce=${nonce}`, {
        headers: {
          cookie: `waooaw.logout-continuation=${nonce}; next-auth.session-token=local-session`,
        },
      })
    );
    const location = new URL(requiredHeader(response, 'location'));

    expect(response.status).toBe(303);
    expect(location.origin).toBe('https://identity.example');
    expect(location.searchParams.get('id_token_hint')).toBe('server-held-id-token');
    expect(response.headers.get('set-cookie')).toContain(
      'waooaw.logout-continuation=; Path=/api/auth/keycloak-logout;'
    );
    expect(response.headers.get('set-cookie')).toContain('next-auth.session-token=;');
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
      'https://app.example/'
    );
  });
});
