import 'server-only';

import { hasFounderClaim } from '@/lib/auth';

const DEFAULT_ADMIN_EMAIL = 'yogesh.khandge@dlaisd.com';
const DEFAULT_TENANT_ID = '0471534c-1bbe-40ab-ae65-3f721b62582c';
const DEFAULT_CLIENT_ID = '710af8d6-8e2c-4f9d-9b1c-2230de9de1f8';
const KEY_VAULT_AUDIENCES = new Set([
  'https://vault.azure.net',
  'https://vault.azure.net/',
  'cfa8b339-82a2-471a-a3c9-0fc0be7a4093',
]);

interface TokenClaims {
  aud?: unknown;
  email?: unknown;
  email_verified?: unknown;
  exp?: unknown;
  preferred_username?: unknown;
  scp?: unknown;
  tid?: unknown;
  upn?: unknown;
  [key: string]: unknown;
}

export interface KeyVaultTarget {
  clientId: string;
  environment: 'codespace' | 'demo' | 'uat';
  tenantId: string;
  vaultUrl: string;
}

function claimsFromToken(token: string): TokenClaims | undefined {
  try {
    const payload = token.split('.')[1];
    return payload ? (JSON.parse(Buffer.from(payload, 'base64url').toString('utf8')) as TokenClaims) : undefined;
  } catch {
    return undefined;
  }
}

function claimEmail(claims: TokenClaims): string | undefined {
  const candidate = claims.email ?? claims.preferred_username ?? claims.upn;
  return typeof candidate === 'string' ? candidate.trim().toLowerCase() : undefined;
}

export function keyVaultAdminEmail(): string {
  return (process.env.KEY_VAULT_ADMIN_EMAIL ?? DEFAULT_ADMIN_EMAIL).trim().toLowerCase();
}

export function isKeyVaultPortalAdministrator(accessToken: string): boolean {
  const claims = claimsFromToken(accessToken);
  return Boolean(
    claims && claimEmail(claims) === keyVaultAdminEmail() && claims.email_verified === true && hasFounderClaim(claims)
  );
}

export function keyVaultTarget(): KeyVaultTarget | undefined {
  const configuredEnvironment = process.env.WAOOAW_ENVIRONMENT?.trim().toLowerCase();
  const environment = process.env.AUTH_PREVIEW_DEPLOYMENT_ID ? 'codespace' : configuredEnvironment;
  if (environment !== 'codespace' && environment !== 'demo' && environment !== 'uat') return undefined;
  const defaultVaultUrl = {
    codespace: 'https://waooaw-dev-kv.vault.azure.net',
    demo: 'https://kv-waooaw-demo.vault.azure.net',
    uat: 'https://kv-waooaw-uat.vault.azure.net',
  }[environment];
  const vaultUrl = (process.env.AZURE_KEY_VAULT_URL ?? defaultVaultUrl).replace(/\/$/, '');
  if (!/^https:\/\/[a-z0-9-]+\.vault\.azure\.net$/i.test(vaultUrl)) return undefined;
  return {
    clientId: process.env.AZURE_KEY_VAULT_WRITER_CLIENT_ID ?? DEFAULT_CLIENT_ID,
    environment,
    tenantId: process.env.AZURE_TENANT_ID ?? DEFAULT_TENANT_ID,
    vaultUrl,
  };
}

export function isAuthorizedAzureVaultToken(accessToken: string, target: KeyVaultTarget): boolean {
  const claims = claimsFromToken(accessToken);
  const scopes = typeof claims?.scp === 'string' ? claims.scp.split(' ') : [];
  return Boolean(
    claims &&
      claims.tid === target.tenantId &&
      KEY_VAULT_AUDIENCES.has(String(claims.aud)) &&
      claimEmail(claims) === keyVaultAdminEmail() &&
      typeof claims.exp === 'number' &&
      claims.exp > Math.floor(Date.now() / 1000) &&
      scopes.includes('user_impersonation')
  );
}

export function isValidSecretName(name: string): boolean {
  return /^[0-9A-Za-z-]{1,127}$/.test(name);
}
