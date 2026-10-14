import 'server-only';

import { createPublicKey, verify, type JsonWebKey } from 'node:crypto';

const logoutEvent = 'http://schemas.openid.net/event/backchannel-logout';

interface LogoutClaims {
  iss?: unknown;
  aud?: unknown;
  iat?: unknown;
  exp?: unknown;
  jti?: unknown;
  sid?: unknown;
  sub?: unknown;
  nonce?: unknown;
  events?: unknown;
}

export interface ValidatedBackchannelLogout {
  issuer: string;
  clientId: string;
  issuedAt: Date;
  expiresAt: Date;
  jti: string;
  sid?: string;
  subject?: string;
}

function decodePart(value: string): Record<string, unknown> {
  return JSON.parse(Buffer.from(value, 'base64url').toString('utf8')) as Record<string, unknown>;
}

export async function validateBackchannelLogout(
  compactToken: string,
  environment: NodeJS.ProcessEnv = process.env,
  nowSeconds = Math.floor(Date.now() / 1000)
): Promise<ValidatedBackchannelLogout> {
  const issuer = environment.KEYCLOAK_EXPECTED_ISSUER ?? environment.KEYCLOAK_ISSUER;
  const clientId = environment.KEYCLOAK_CLIENT_ID;
  if (!issuer || !clientId || issuer.startsWith('http://')) throw new Error('Pinned logout authority is unavailable');
  const parts = compactToken.split('.');
  if (parts.length !== 3 || parts.some((part) => !part)) throw new Error('Logout token is invalid');
  const header = decodePart(parts[0]);
  const claims = decodePart(parts[1]) as LogoutClaims;
  if (header.alg !== 'RS256' || typeof header.kid !== 'string') throw new Error('Logout token algorithm is invalid');
  const jwksUrl = `${issuer.replace(/\/$/, '')}/protocol/openid-connect/certs`;
  const response = await fetch(jwksUrl, {
    cache: 'no-store',
    signal: AbortSignal.timeout(5_000),
  });
  if (!response.ok) throw new Error('Logout signing keys are unavailable');
  const document = (await response.json()) as { keys?: JsonWebKey[] };
  const jwk = document.keys?.find(
    (candidate) =>
      candidate.kid === header.kid &&
      candidate.kty === 'RSA' &&
      (!candidate.alg || candidate.alg === 'RS256') &&
      (!candidate.use || candidate.use === 'sig')
  );
  if (!jwk) throw new Error('Logout signing key is unavailable');
  if (
    !verify(
      'RSA-SHA256',
      Buffer.from(`${parts[0]}.${parts[1]}`, 'ascii'),
      createPublicKey({ key: jwk, format: 'jwk' }),
      Buffer.from(parts[2], 'base64url')
    )
  )
    throw new Error('Logout signature is invalid');
  const audience = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
  const events =
    claims.events && typeof claims.events === 'object' ? (claims.events as Record<string, unknown>) : undefined;
  if (
    claims.iss !== issuer.replace(/\/$/, '') ||
    !audience.includes(clientId) ||
    typeof claims.iat !== 'number' ||
    claims.iat < nowSeconds - 300 ||
    claims.iat > nowSeconds + 60 ||
    typeof claims.jti !== 'string' ||
    !claims.jti ||
    claims.nonce !== undefined ||
    !events ||
    !(logoutEvent in events) ||
    (typeof claims.sid === 'string') === (typeof claims.sub === 'string')
  )
    throw new Error('Logout claims are invalid');
  const expiresAt =
    typeof claims.exp === 'number' && claims.exp >= nowSeconds && claims.exp <= claims.iat + 600
      ? claims.exp
      : claims.iat + 600;
  return {
    issuer: issuer.replace(/\/$/, ''),
    clientId,
    issuedAt: new Date(claims.iat * 1000),
    expiresAt: new Date(expiresAt * 1000),
    jti: claims.jti,
    sid: typeof claims.sid === 'string' ? claims.sid : undefined,
    subject: typeof claims.sub === 'string' ? claims.sub : undefined,
  };
}
