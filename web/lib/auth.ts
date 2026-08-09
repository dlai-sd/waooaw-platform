import type { Session, NextAuthOptions } from 'next-auth';
import type { JWT } from 'next-auth/jwt';
import KeycloakProvider from 'next-auth/providers/keycloak';

// Implements: architecture/reference/ux/hybrid-application-shell.md §Authentication Boundaries
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

const keycloakIssuer = process.env.KEYCLOAK_ISSUER ?? 'http://localhost:8080/realms/waooaw';

export function hasFounderClaim(profile: unknown): boolean {
  if (!profile || typeof profile !== 'object') return false;
  const claims = profile as Record<string, unknown>;
  if (claims.founder === true) return true;
  const realmAccess = claims.realm_access;
  if (!realmAccess || typeof realmAccess !== 'object') return false;
  const roles = (realmAccess as Record<string, unknown>).roles;
  return Array.isArray(roles) && roles.includes('founder');
}

export function projectSession(session: Session, token: JWT): Session {
  session.authenticated = typeof token.accessToken === 'string';
  session.founder = token.founder === true;
  return session;
}

export const authOptions: NextAuthOptions = {
  providers: [
    KeycloakProvider({
      clientId: process.env.KEYCLOAK_CLIENT_ID ?? 'waooaw-web',
      clientSecret: process.env.KEYCLOAK_CLIENT_SECRET ?? 'local-development-only',
      issuer: keycloakIssuer,
    }),
  ],
  session: { strategy: 'jwt' },
  callbacks: {
    jwt({ token, account, profile }) {
      if (account?.access_token) token.accessToken = account.access_token;
      if (account) token.founder = hasFounderClaim(profile);
      return token;
    },
    session({ session, token }) {
      return projectSession(session, token);
    },
  },
  pages: { signIn: '/login', error: '/auth/error' },
};