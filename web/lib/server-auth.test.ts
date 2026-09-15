jest.mock('server-only', () => ({}));

import { getToken } from 'next-auth/jwt';
import { cookies, headers } from 'next/headers';
import type { NextRequest } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { accessTokenFromRequest, getServerAccessToken } from './server-auth';

jest.mock('next-auth/jwt', () => ({ getToken: jest.fn() }));
jest.mock('next/headers', () => ({ cookies: jest.fn(), headers: jest.fn() }));
jest.mock('@/lib/auth', () => ({ activeAccessToken: jest.fn() }));

it('uses only a persisted active access token for an internal API call', async () => {
  const token = {
    accessToken: 'expired-token',
    accessTokenExpiresAt: 1,
    refreshToken: 'server-held-refresh-token',
  };
  jest.mocked(getToken).mockResolvedValue(token);
  jest.mocked(activeAccessToken).mockReturnValue('active-token');
  const request = {} as NextRequest;

  await expect(accessTokenFromRequest(request)).resolves.toBe('active-token');

  expect(activeAccessToken).toHaveBeenCalledWith(token);
});

it('exposes persisted chunked cookies through the request API NextAuth consumes', async () => {
  const persistedCookies = [
    { name: '__Secure-next-auth.session-token.0', value: 'first' },
    { name: '__Secure-next-auth.session-token.1', value: 'second' },
  ];
  jest.mocked(cookies).mockResolvedValue({ getAll: () => persistedCookies } as never);
  jest.mocked(headers).mockResolvedValue(new Headers({
    cookie: '__Secure-next-auth.session-token.0=first; __Secure-next-auth.session-token.1=second',
  }) as never);
  jest.mocked(getToken).mockResolvedValue({ accessToken: 'access-token' });
  jest.mocked(activeAccessToken).mockReturnValue('access-token');

  await expect(getServerAccessToken()).resolves.toBe('access-token');

  const request = jest.mocked(getToken).mock.calls.at(-1)![0].req as NextRequest;
  expect(request.cookies.getAll()).toEqual(persistedCookies);
});