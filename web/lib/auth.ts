import type { Session, NextAuthOptions } from 'next-auth';
import type { JWT } from 'next-auth/jwt';
import KeycloakProvider from 'next-auth/providers/keycloak';

// Implements: architecture/reference/ux/hybrid-application-shell.md §Authentication Boundaries
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

interface KeycloakEnvironment {
  KEYCLOAK_PUBLIC_CLIENT?: string;
  KEYCLOAK_CLIENT_ID?: string;
  KEYCLOAK_CLIENT_SECRET?: string;
  KEYCLOAK_ISSUER?: string;
}

export function keycloakClientConfig(environment: KeycloakEnvironment = process.env as KeycloakEnvironment) {
  const publicClient = environment.KEYCLOAK_PUBLIC_CLIENT === 'true';
  return {
    clientId: environment.KEYCLOAK_CLIENT_ID ?? 'waooaw-web',
    clientSecret: publicClient ? '' : environment.KEYCLOAK_CLIENT_SECRET ?? 'local-development-only',
    issuer: environment.KEYCLOAK_ISSUER ?? 'http://localhost:8080/realms/waooaw',
    ...(publicClient ? { client: { token_endpoint_auth_method: 'none' as const } } : {}),
  };
}

const keycloakClient = keycloakClientConfig();

function brokeredKeycloakProvider(id: string, name: string, brokerAlias: string) {
  return {
    ...KeycloakProvider(keycloakClient),
    id,
    name,
    authorization: { params: { scope: 'openid profile email', kc_idp_hint: brokerAlias } },
  };
}

export function hasFounderClaim(profile: unknown): boolean {
  if (!profile || typeof profile !== 'object') return false;
  const claims = profile as Record<string, unknown>;
  if (claims.founder === true) return true;
  const realmAccess = claims.realm_access;
  if (!realmAccess || typeof realmAccess !== 'object') return false;
  const roles = (realmAccess as Record<string, unknown>).roles;
  return Array.isArray(roles) && roles.includes('founder');
}

export function activeAccessToken(token: JWT, nowSeconds = Math.floor(Date.now() / 1000)): string | undefined {
  return typeof token.accessToken === 'string'
    && typeof token.accessTokenExpiresAt === 'number'
    && token.accessTokenExpiresAt > nowSeconds
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

function purgeAuthentication(token: JWT): JWT {
  delete token.accessToken;
  delete token.accessTokenExpiresAt;
  delete token.refreshToken;
  token.founder = false;
  return token;
}

async function refreshAccessToken(token: JWT): Promise<JWT> {
  if (typeof token.refreshToken !== 'string') return purgeAuthentication(token);
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: token.refreshToken,
    client_id: keycloakClient.clientId,
  });
  if (keycloakClient.clientSecret) body.set('client_secret', keycloakClient.clientSecret);

  try {
    const response = await fetch(
      `${keycloakClient.issuer.replace(/\/$/, '')}/protocol/openid-connect/token`,
      {
        method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        body,
        cache: 'no-store',
      },
    );
    if (!response.ok) return purgeAuthentication(token);
    const refreshed = await response.json() as {
      access_token?: unknown;
      expires_in?: unknown;
      refresh_token?: unknown;
      id_token?: unknown;
    };
    if (typeof refreshed.access_token !== 'string'
      || typeof refreshed.expires_in !== 'number'
      || !Number.isFinite(refreshed.expires_in)
      || refreshed.expires_in <= 0) return purgeAuthentication(token);

    token.accessToken = refreshed.access_token;
    token.accessTokenExpiresAt = Math.floor(Date.now() / 1000) + refreshed.expires_in;
    if (typeof refreshed.refresh_token === 'string') token.refreshToken = refreshed.refresh_token;
    if (typeof refreshed.id_token === 'string') token.idToken = refreshed.id_token;
    token.founder = hasFounderClaim(accessTokenClaims(refreshed.access_token));
    return token;
  } catch {
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

export const authOptions: NextAuthOptions = {
  providers: [
    KeycloakProvider(keycloakClient),
    brokeredKeycloakProvider('keycloak-google', 'Google', process.env.KEYCLOAK_GOOGLE_BROKER_ALIAS ?? 'google'),
    brokeredKeycloakProvider('keycloak-facebook', 'Facebook', process.env.KEYCLOAK_FACEBOOK_BROKER_ALIAS ?? 'facebook'),
    brokeredKeycloakProvider('keycloak-apple', 'Apple', process.env.KEYCLOAK_APPLE_BROKER_ALIAS ?? 'apple'),
  ],
  session: { strategy: 'jwt' },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
        token.accessTokenExpiresAt = account.expires_at;
      }
      if (account?.refresh_token) token.refreshToken = account.refresh_token;
      if (account?.id_token) token.idToken = account.id_token;
      if (account) token.founder = hasFounderClaim(profile);
      return activeAccessToken(token) ? token : refreshAccessToken(token);
    },
    session({ session, token }) {
      return projectSession(session, token);
    },
  },
  pages: { signIn: '/login', error: '/auth/error' },
};