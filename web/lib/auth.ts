import type { Session, NextAuthOptions } from 'next-auth';
import type { JWT } from 'next-auth/jwt';
import { decode as decodeLegacyJwt, encode as encodeLegacyJwt } from 'next-auth/jwt';
import KeycloakProvider from 'next-auth/providers/keycloak';
import { createHash } from 'node:crypto';
import { persistWebIdentitySecurityEvent, recordWebIdentitySecurityEvent } from '@/lib/identity-security-events';
import { hasFounderClaim } from '@/lib/identity-claims';
import {
  acquireRefreshLease,
  completeRefresh,
  createSession,
  loadSession,
  revokeSession,
} from '@/lib/web-session-store';
import { isApprovedShadowSubject, serverSessionMode } from '@/lib/server-session-mode';

// Implements: architecture/reference/ux/hybrid-application-shell.md §Authentication Boundaries
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

interface KeycloakEnvironment {
  KEYCLOAK_PUBLIC_CLIENT?: string;
  KEYCLOAK_CLIENT_ID?: string;
  KEYCLOAK_CLIENT_SECRET?: string;
  KEYCLOAK_ISSUER?: string;
  KEYCLOAK_EXPECTED_ISSUER?: string;
  NODE_ENV?: string;
}

interface PreviewSessionEnvironment {
  AUTH_PREVIEW_DEPLOYMENT_ID?: string;
  AUTH_PREVIEW_SESSION_MAX_AGE_SECONDS?: string;
}

export function keycloakClientConfig(environment: KeycloakEnvironment = process.env as KeycloakEnvironment) {
  const publicClient = environment.KEYCLOAK_PUBLIC_CLIENT === 'true';
  const issuerValue = environment.KEYCLOAK_ISSUER ?? 'http://localhost:8080/realms/waooaw';
  const issuer = new URL(issuerValue);
  if (
    issuer.username ||
    issuer.password ||
    issuer.search ||
    issuer.hash ||
    !/^\/realms\/[A-Za-z0-9._-]+$/.test(issuer.pathname) ||
    (environment.NODE_ENV === 'production' && issuer.protocol !== 'https:') ||
    (environment.KEYCLOAK_EXPECTED_ISSUER &&
      issuer.toString().replace(/\/$/, '') !== environment.KEYCLOAK_EXPECTED_ISSUER.replace(/\/$/, ''))
  )
    throw new Error('Pinned Keycloak issuer configuration is invalid');
  return {
    clientId: environment.KEYCLOAK_CLIENT_ID ?? 'waooaw-web',
    clientSecret: publicClient ? '' : (environment.KEYCLOAK_CLIENT_SECRET ?? 'local-development-only'),
    issuer: issuer.toString().replace(/\/$/, ''),
    ...(publicClient ? { client: { token_endpoint_auth_method: 'none' as const } } : {}),
  };
}

const keycloakClient = keycloakClientConfig();

function brokeredKeycloakProvider(
  id: string,
  name: string,
  brokerAlias: string,
  authorization: Record<string, string> = {}
) {
  return {
    ...KeycloakProvider(keycloakClient),
    id,
    name,
    authorization: { params: { scope: 'openid profile email', kc_idp_hint: brokerAlias, ...authorization } },
  };
}

export { hasFounderClaim } from '@/lib/identity-claims';

export function activeAccessToken(token: JWT, nowSeconds = Math.floor(Date.now() / 1000)): string | undefined {
  return typeof token.accessToken === 'string' &&
    token.accessToken.trim().length > 0 &&
    typeof token.accessTokenExpiresAt === 'number' &&
    token.accessTokenExpiresAt > nowSeconds
    ? token.accessToken
    : undefined;
}

function accessTokenClaims(accessToken: string): unknown {
  try {
    const payload = accessToken.split('.')[1];
    return payload ? JSON.parse(Buffer.from(payload, 'base64url').toString('utf8')) : undefined;
  } catch {
    return undefined;
  }
}

function globalUserReference(profile: Record<string, unknown>): string {
  const issuer = typeof profile.iss === 'string' ? profile.iss : '';
  const subject = typeof profile.sub === 'string' ? profile.sub : '';
  if (!issuer || !subject) throw new Error('Validated issuer and subject are required');
  const bytes = createHash('sha256').update(`${issuer}\u001f${subject}`, 'utf8').digest().subarray(0, 16);
  bytes[6] = (bytes[6] & 0x0f) | 0x50;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = bytes.toString('hex');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function purgeAuthentication(token: JWT): JWT {
  Reflect.deleteProperty(token, 'accessToken');
  Reflect.deleteProperty(token, 'accessTokenExpiresAt');
  Reflect.deleteProperty(token, 'refreshToken');
  token.founder = false;
  return token;
}

export function previewSessionMaxAge(
  environment: PreviewSessionEnvironment = process.env as PreviewSessionEnvironment
): number | undefined {
  if (!environment.AUTH_PREVIEW_DEPLOYMENT_ID) return undefined;
  const seconds = Number(environment.AUTH_PREVIEW_SESSION_MAX_AGE_SECONDS ?? '3600');
  return Number.isInteger(seconds) && seconds >= 300 && seconds <= 28_800 ? seconds : 3600;
}

export function bindPreviewDeployment(
  token: JWT,
  accountReceived: boolean,
  deploymentId = process.env.AUTH_PREVIEW_DEPLOYMENT_ID
): JWT {
  if (!deploymentId) return token;
  if (accountReceived) {
    token.previewDeploymentId = deploymentId;
    return token;
  }
  if (token.previewDeploymentId === deploymentId) return token;
  const purged = purgeAuthentication(token);
  purged.previewDeploymentId = deploymentId;
  return purged;
}

async function refreshAccessToken(token: JWT): Promise<JWT> {
  const correlationId = crypto.randomUUID();
  if (typeof token.refreshToken !== 'string') {
    await recordWebIdentitySecurityEvent({
      correlationId,
      eventType: 'SESSION_EXPIRY',
      providerClass: 'INTERNAL',
      outcome: 'DENIED',
      reasonCode: 'REFRESH_TOKEN_ABSENT',
      assuranceClass: 'UNKNOWN',
    });
    return purgeAuthentication(token);
  }
  let leaseOwner: string | null;
  try {
    leaseOwner = await acquireRefreshLease(token);
    if (!leaseOwner) {
      if (typeof token.sessionHandle !== 'string') return purgeAuthentication(token);
      for (let attempt = 0; attempt < 10; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        const refreshed = await loadSession(token.sessionHandle);
        if (refreshed && activeAccessToken(refreshed)) return refreshed;
      }
      await recordWebIdentitySecurityEvent({
        correlationId,
        eventType: 'REFRESH_FAILURE',
        providerClass: 'INTERNAL',
        outcome: 'FAILED',
        reasonCode: 'REFRESH_RESULT_UNAVAILABLE',
        assuranceClass: 'UNKNOWN',
      });
      return purgeAuthentication(token);
    }
  } catch {
    await recordWebIdentitySecurityEvent({
      correlationId,
      eventType: 'REFRESH_FAILURE',
      providerClass: 'INTERNAL',
      outcome: 'FAILED',
      reasonCode: 'SESSION_STORE_UNAVAILABLE',
      assuranceClass: 'UNKNOWN',
    });
    return purgeAuthentication(token);
  }
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: token.refreshToken,
    client_id: keycloakClient.clientId,
  });
  if (keycloakClient.clientSecret) body.set('client_secret', keycloakClient.clientSecret);

  try {
    const response = await fetch(`${keycloakClient.issuer.replace(/\/$/, '')}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body,
      cache: 'no-store',
    });
    if (!response.ok) {
      await revokeSession(token, 'REFRESH_REJECTED');
      await recordWebIdentitySecurityEvent({
        correlationId,
        eventType: 'REFRESH_FAILURE',
        providerClass: 'INTERNAL',
        outcome: 'FAILED',
        reasonCode: 'TOKEN_ENDPOINT_REJECTED',
        assuranceClass: 'UNKNOWN',
      });
      return purgeAuthentication(token);
    }
    const refreshed = (await response.json()) as {
      access_token?: unknown;
      expires_in?: unknown;
      refresh_token?: unknown;
      id_token?: unknown;
    };
    if (
      typeof refreshed.access_token !== 'string' ||
      refreshed.access_token.trim().length === 0 ||
      typeof refreshed.expires_in !== 'number' ||
      !Number.isFinite(refreshed.expires_in) ||
      refreshed.expires_in <= 0
    ) {
      await revokeSession(token, 'REFRESH_RESPONSE_INVALID');
      await recordWebIdentitySecurityEvent({
        correlationId,
        eventType: 'REFRESH_FAILURE',
        providerClass: 'INTERNAL',
        outcome: 'FAILED',
        reasonCode: 'TOKEN_RESPONSE_INVALID',
        assuranceClass: 'UNKNOWN',
      });
      return purgeAuthentication(token);
    }

    token.accessToken = refreshed.access_token;
    token.accessTokenExpiresAt = Math.floor(Date.now() / 1000) + refreshed.expires_in;
    if (typeof refreshed.refresh_token === 'string' && refreshed.refresh_token.trim()) {
      token.refreshToken = refreshed.refresh_token;
    }
    if (typeof refreshed.id_token === 'string' && refreshed.id_token.trim()) token.idToken = refreshed.id_token;
    token.founder = hasFounderClaim(accessTokenClaims(refreshed.access_token));
    if (!(await completeRefresh(token, leaseOwner))) {
      await revokeSession(token, 'REFRESH_COMMIT_FAILED');
      return purgeAuthentication(token);
    }
    token.refreshVersion = (token.refreshVersion ?? 0) + 1;
    try {
      await persistWebIdentitySecurityEvent({
        correlationId,
        eventType: 'REFRESH_SUCCESS',
        providerClass: 'INTERNAL',
        outcome: 'SUCCEEDED',
        reasonCode: 'TOKEN_ROTATED',
        assuranceClass: 'AAL2',
      });
    } catch {
      await recordWebIdentitySecurityEvent({
        correlationId,
        eventType: 'REFRESH_FAILURE',
        providerClass: 'INTERNAL',
        outcome: 'FAILED',
        reasonCode: 'EVENT_PERSISTENCE_UNAVAILABLE',
        assuranceClass: 'UNKNOWN',
      });
      return purgeAuthentication(token);
    }
    return token;
  } catch {
    await recordWebIdentitySecurityEvent({
      correlationId,
      eventType: 'REFRESH_FAILURE',
      providerClass: 'INTERNAL',
      outcome: 'FAILED',
      reasonCode: 'TOKEN_ENDPOINT_UNAVAILABLE',
      assuranceClass: 'UNKNOWN',
    });
    return purgeAuthentication(token);
  }
}

export async function resolveAccessToken(token: JWT): Promise<string | undefined> {
  const current = activeAccessToken(token);
  if (current) return current;
  return activeAccessToken(await refreshAccessToken(token));
}

export function projectSession(session: Session, token: JWT, nowSeconds?: number): Session {
  const authenticated = activeAccessToken(token, nowSeconds) !== undefined;
  session.authenticated = authenticated;
  session.founder = authenticated && token.founder === true;
  return session;
}

const sessionMaxAge = previewSessionMaxAge();
const sessionMode = serverSessionMode();

export const authOptions: NextAuthOptions = {
  providers: [
    KeycloakProvider(keycloakClient),
    brokeredKeycloakProvider('keycloak-google', 'Google', process.env.KEYCLOAK_GOOGLE_BROKER_ALIAS ?? 'google', {
      prompt: 'select_account',
      max_age: '0',
    }),
    brokeredKeycloakProvider('keycloak-facebook', 'Facebook', process.env.KEYCLOAK_FACEBOOK_BROKER_ALIAS ?? 'facebook'),
    brokeredKeycloakProvider('keycloak-apple', 'Apple', process.env.KEYCLOAK_APPLE_BROKER_ALIAS ?? 'apple'),
  ],
  session: { strategy: 'jwt', ...(sessionMaxAge ? { maxAge: sessionMaxAge } : {}) },
  jwt: {
    ...(sessionMaxAge ? { maxAge: sessionMaxAge } : {}),
    encode:
      sessionMode === 'enforced'
        ? async ({ token }) => (typeof token?.sessionHandle === 'string' ? token.sessionHandle : '')
        : encodeLegacyJwt,
    decode: sessionMode === 'enforced' ? async ({ token }) => (token ? loadSession(token) : null) : decodeLegacyJwt,
  },
  ...(sessionMode === 'enforced'
    ? {
        cookies: {
          sessionToken: {
            name: '__Host-waooaw-session',
            options: {
              httpOnly: true,
              sameSite: 'lax' as const,
              path: '/',
              secure: true,
            },
          },
        },
      }
    : {}),
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
        token.accessTokenExpiresAt = account.expires_at;
      }
      if (account?.refresh_token) token.refreshToken = account.refresh_token;
      if (account?.id_token) token.idToken = account.id_token;
      if (account) token.founder = hasFounderClaim(profile);
      token = bindPreviewDeployment(token, Boolean(account));
      if (account) {
        const idTokenClaims = typeof account.id_token === 'string' ? accessTokenClaims(account.id_token) : undefined;
        const validatedProfile = {
          ...(profile && typeof profile === 'object' ? profile : {}),
          ...(idTokenClaims && typeof idTokenClaims === 'object' ? idTokenClaims : {}),
        } as Record<string, unknown>;
        if (!activeAccessToken(token)) return purgeAuthentication(token);
        const globalUserId = globalUserReference(validatedProfile);
        if (sessionMode === 'enforced') return createSession(token, validatedProfile, globalUserId);
        if (sessionMode === 'shadow' && isApprovedShadowSubject(String(validatedProfile.sub ?? ''))) {
          try {
            const shadow = await createSession(token, validatedProfile, globalUserId);
            await revokeSession(shadow, 'SHADOW_COMPARISON');
          } catch (error) {
            console.error('Server-session shadow comparison failed', {
              cause: error instanceof Error ? error.name : 'UnknownError',
            });
          }
        }
        return token;
      }
      return activeAccessToken(token) ? token : refreshAccessToken(token);
    },
    session({ session, token }) {
      return projectSession(session, token);
    },
  },
  events: {
    async signOut({ token }) {
      if (sessionMode === 'enforced') await revokeSession(token, 'LOCAL_LOGOUT');
    },
  },
  pages: { signIn: '/login', error: '/auth/error' },
};
