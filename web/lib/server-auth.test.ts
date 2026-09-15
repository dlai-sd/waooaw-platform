jest.mock('server-only', () => ({}));

import { getToken } from 'next-auth/jwt';
import type { NextRequest } from 'next/server';
import { resolveAccessToken } from '@/lib/auth';
import { accessTokenFromRequest } from './server-auth';

jest.mock('next-auth/jwt', () => ({ getToken: jest.fn() }));
jest.mock('@/lib/auth', () => ({ activeAccessToken: jest.fn(), resolveAccessToken: jest.fn() }));

it('resolves a renewed access token before an internal API call', async () => {
  const token = {
    accessToken: 'expired-token',
    accessTokenExpiresAt: 1,
    refreshToken: 'server-held-refresh-token',
  };
  jest.mocked(getToken).mockResolvedValue(token);
  jest.mocked(resolveAccessToken).mockResolvedValue('renewed-token');
  const request = {} as NextRequest;

  await expect(accessTokenFromRequest(request)).resolves.toBe('renewed-token');

  expect(resolveAccessToken).toHaveBeenCalledWith(token);
});