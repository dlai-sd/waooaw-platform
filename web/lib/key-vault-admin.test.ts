import {
  isAuthorizedAzureVaultToken,
  isKeyVaultPortalAdministrator,
  isValidSecretName,
  keyVaultTarget,
} from './key-vault-admin';

function token(claims: Record<string, unknown>): string {
  return `${Buffer.from('{}').toString('base64url')}.${Buffer.from(JSON.stringify(claims)).toString('base64url')}.signature`;
}

const originalEnvironment = process.env;

afterEach(() => {
  process.env = originalEnvironment;
});

test('authorizes only the verified Founder email', () => {
  const authorized = token({
    email: 'yogesh.khandge@dlaisd.com',
    email_verified: true,
    realm_access: { roles: ['founder'] },
  });
  expect(isKeyVaultPortalAdministrator(authorized)).toBe(true);
  expect(
    isKeyVaultPortalAdministrator(token({ email: 'yogesh.khandge@dlaisd.com', email_verified: false, founder: true }))
  ).toBe(false);
  expect(isKeyVaultPortalAdministrator(token({ email: 'other@dlaisd.com', email_verified: true, founder: true }))).toBe(
    false
  );
});

test('binds Codespace, demo, and UAT to server-owned vault targets', () => {
  process.env = { ...originalEnvironment, AUTH_PREVIEW_DEPLOYMENT_ID: 'preview', WAOOAW_ENVIRONMENT: 'uat' };
  expect(keyVaultTarget()?.vaultUrl).toBe('https://waooaw-dev-kv.vault.azure.net');
  process.env = { ...originalEnvironment, AUTH_PREVIEW_DEPLOYMENT_ID: '', WAOOAW_ENVIRONMENT: 'demo' };
  expect(keyVaultTarget()?.vaultUrl).toBe('https://kv-waooaw-demo.vault.azure.net');
  process.env = { ...originalEnvironment, AUTH_PREVIEW_DEPLOYMENT_ID: '', WAOOAW_ENVIRONMENT: 'production' };
  expect(keyVaultTarget()).toBeUndefined();
});

test('requires an unexpired same-tenant Key Vault token for the same administrator', () => {
  const target = {
    clientId: 'client',
    environment: 'demo' as const,
    tenantId: 'tenant',
    vaultUrl: 'https://kv-waooaw-demo.vault.azure.net',
  };
  const claims = {
    aud: 'https://vault.azure.net',
    exp: Math.floor(Date.now() / 1000) + 300,
    preferred_username: 'yogesh.khandge@dlaisd.com',
    scp: 'user_impersonation',
    tid: 'tenant',
  };
  expect(isAuthorizedAzureVaultToken(token(claims), target)).toBe(true);
  expect(isAuthorizedAzureVaultToken(token({ ...claims, aud: 'cfa8b339-82a2-471a-a3c9-0fc0be7a4093' }), target)).toBe(
    true
  );
  expect(isAuthorizedAzureVaultToken(token({ ...claims, tid: 'other' }), target)).toBe(false);
  expect(isAuthorizedAzureVaultToken(token({ ...claims, preferred_username: 'other@dlaisd.com' }), target)).toBe(false);
});

test('accepts only Azure Key Vault secret names', () => {
  expect(isValidSecretName('razorpay-test-key-secret')).toBe(true);
  expect(isValidSecretName('../other')).toBe(false);
  expect(isValidSecretName('')).toBe(false);
});
