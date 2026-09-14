/** @jest-environment node */

jest.mock('next-auth/jwt', () => ({ getToken: jest.fn() }));

import { getToken } from 'next-auth/jwt';
import { NextRequest } from 'next/server';
import { POST } from './route';

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
        cookie: 'next-auth.session-token=local-session; next-auth.session-token.0=chunk; __Host-next-auth.csrf-token=csrf; next-auth.callback-url=%2Fhome; waooaw-theme=dark; unrelated=preserve',
      },
    });

    const response = await POST(request);
    const location = new URL(response.headers.get('location')!);

    expect(response.status).toBe(303);
    expect(location.origin + location.pathname).toBe('https://identity.example/realms/waooaw/protocol/openid-connect/logout');
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

  it('rejects a cross-origin logout submission', async () => {
    const response = await POST(new NextRequest('https://app.example/api/auth/keycloak-logout', {
      method: 'POST', headers: { origin: 'https://attacker.example' },
    }));

    expect(response.status).toBe(403);
    expect(getToken).not.toHaveBeenCalled();
  });

  it('does not trust a forged request host for the post-logout target', async () => {
    const response = await POST(new NextRequest('https://attacker.example/api/auth/keycloak-logout', {
      method: 'POST', headers: { origin: 'https://app.example' },
    }));

    expect(new URL(response.headers.get('location')!).searchParams.get('post_logout_redirect_uri'))
      .toBe('https://app.example/');
  });
});