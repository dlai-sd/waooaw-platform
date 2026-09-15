jest.mock('server-only', () => ({}));

import { getToken } from 'next-auth/jwt';
import type { NextRequest } from 'next/server';
import { activeAccessToken } from '@/lib/auth';
import { accessTokenFromRequest } from './server-auth';

jest.mock('next-auth/jwt', () => ({ getToken: jest.fn() }));
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