/** @jest-environment node */

import { NextRequest } from 'next/server';
import middleware from '../../middleware';

describe('session migration middleware', () => {
  afterEach(() => {
    Reflect.deleteProperty(process.env, 'WAOOAW_SERVER_SESSION_MODE');
  });

  it('expires and rejects a legacy JWT cookie while enforced', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'enforced';
    const response = await middleware(
      new NextRequest('https://app.example/settings', {
        headers: { cookie: 'next-auth.session-token=legacy-jwt' },
      })
    );

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://app.example/login');
    expect(response.headers.get('set-cookie')).toContain('next-auth.session-token=;');
  });

  it('keeps the legacy JWT cookie authoritative while disabled', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'disabled';
    const response = await middleware(
      new NextRequest('https://app.example/settings', {
        headers: { cookie: 'next-auth.session-token=legacy-jwt' },
      })
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('x-middleware-next')).toBe('1');
    expect(response.headers.get('set-cookie')).toBeNull();
  });

  it('accepts a chunked legacy JWT cookie while disabled', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'disabled';
    const response = await middleware(
      new NextRequest('https://app.example/home', {
        headers: {
          cookie: '__Secure-next-auth.session-token.0=chunk-a; __Secure-next-auth.session-token.1=chunk-b',
        },
      })
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('x-middleware-next')).toBe('1');
  });

  it('expires every chunk of a legacy JWT cookie while enforced', async () => {
    process.env.WAOOAW_SERVER_SESSION_MODE = 'enforced';
    const response = await middleware(
      new NextRequest('https://app.example/home', {
        headers: {
          cookie: '__Secure-next-auth.session-token.0=chunk-a; __Secure-next-auth.session-token.1=chunk-b',
        },
      })
    );

    expect(response.status).toBe(307);
    const cleared = response.headers.get('set-cookie') ?? '';
    expect(cleared).toContain('__Secure-next-auth.session-token.0=;');
    expect(cleared).toContain('__Secure-next-auth.session-token.1=;');
  });
});
