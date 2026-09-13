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
    jwt({ token, account, profile }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
        token.accessTokenExpiresAt = account.expires_at;
      }
      if (account) token.founder = hasFounderClaim(profile);
      if (!activeAccessToken(token)) {
        delete token.accessToken;
        delete token.accessTokenExpiresAt;
        token.founder = false;
      }
      return token;
    },
    session({ session, token }) {
      return projectSession(session, token);
    },
  },
  pages: { signIn: '/login', error: '/auth/error' },
};