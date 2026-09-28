/** @jest-environment node */
import type { NextRequest } from 'next/server';
import { POST } from './route';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { isAuthorizedAzureVaultToken, isKeyVaultPortalAdministrator, keyVaultTarget } from '@/lib/key-vault-admin';

jest.mock('@/lib/server-auth', () => ({ accessTokenFromRequest: jest.fn() }));
jest.mock('@/lib/key-vault-admin', () => ({
  isAuthorizedAzureVaultToken: jest.fn(),
  isKeyVaultPortalAdministrator: jest.fn(),
  isValidSecretName: (name: string) => /^[0-9A-Za-z-]{1,127}$/.test(name),
  keyVaultTarget: jest.fn(),
}));

const target = {
  clientId: 'client',
  environment: 'demo' as const,
  tenantId: 'tenant',
  vaultUrl: 'https://kv-waooaw-demo.vault.azure.net',
};

beforeEach(() => {
  process.env.NEXTAUTH_URL = 'https://portal.example';
  jest.mocked(accessTokenFromRequest).mockResolvedValue('portal-token');
  jest.mocked(isKeyVaultPortalAdministrator).mockReturnValue(true);
  jest.mocked(isAuthorizedAzureVaultToken).mockReturnValue(true);
  jest.mocked(keyVaultTarget).mockReturnValue(target);
  global.fetch = jest.fn().mockResolvedValue(new Response('{}', { status: 200 }));
});

function request(body: unknown, origin: string | undefined = 'https://portal.example') {
  return {
    headers: new Headers({
      Authorization: 'Bearer azure-token',
      'Content-Type': 'application/json',
      ...(origin ? { Origin: origin } : {}),
    }),
    json: async () => body,
    nextUrl: new URL('https://portal.example/api/admin/azure-key-vault'),
  } as NextRequest;
}

test('writes a secret without returning its value', async () => {
  const response = await POST(request({ name: 'razorpay-test-key-secret', value: 'sensitive-value' }));
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ name: 'razorpay-test-key-secret', environment: 'demo', status: 'SAVED' });
  expect(global.fetch).toHaveBeenCalledWith(
    'https://kv-waooaw-demo.vault.azure.net/secrets/razorpay-test-key-secret?api-version=7.4',
    expect.objectContaining({ method: 'PUT', body: expect.stringContaining('sensitive-value') })
  );
});

test('rejects cross-origin and unauthorized portal requests before Azure', async () => {
  expect((await POST(request({ name: 'valid-name', value: 'value' }, 'https://attacker.example'))).status).toBe(403);
  jest.mocked(isKeyVaultPortalAdministrator).mockReturnValue(false);
  expect((await POST(request({ name: 'valid-name', value: 'value' }))).status).toBe(403);
  expect(global.fetch).not.toHaveBeenCalled();
});

test('accepts a proxy-preserved same-origin browser request when Origin is omitted', async () => {
  const sameOriginRequest = request({ name: 'razorpay-test-key-id', value: 'sensitive-value' }, undefined);
  sameOriginRequest.headers.set('Sec-Fetch-Site', 'same-origin');

  expect((await POST(sameOriginRequest)).status).toBe(200);
});

test('prefers trusted browser fetch metadata when a proxy rewrites Origin', async () => {
  const sameOriginRequest = request(
    { name: 'razorpay-test-key-id', value: 'sensitive-value' },
    'http://localhost:3000'
  );
  sameOriginRequest.headers.set('Sec-Fetch-Site', 'same-origin');

  expect((await POST(sameOriginRequest)).status).toBe(200);
});

test('rejects browser requests identified as cross-site', async () => {
  const crossSiteRequest = request({ name: 'razorpay-test-key-id', value: 'sensitive-value' });
  crossSiteRequest.headers.set('Sec-Fetch-Site', 'cross-site');

  expect((await POST(crossSiteRequest)).status).toBe(403);
});

test('accepts a canonical same-origin referrer when Origin is omitted', async () => {
  const sameOriginRequest = request({ name: 'razorpay-test-key-id', value: 'sensitive-value' }, undefined);
  sameOriginRequest.headers.set('Referer', 'https://portal.example/admin/azure-key-vault');

  expect((await POST(sameOriginRequest)).status).toBe(200);
});

test('rejects a token for another Azure identity and invalid names', async () => {
  jest.mocked(isAuthorizedAzureVaultToken).mockReturnValue(false);
  expect((await POST(request({ name: 'valid-name', value: 'value' }))).status).toBe(403);
  jest.mocked(isAuthorizedAzureVaultToken).mockReturnValue(true);
  expect((await POST(request({ name: '../invalid', value: 'value' }))).status).toBe(400);
  expect(global.fetch).not.toHaveBeenCalled();
});
