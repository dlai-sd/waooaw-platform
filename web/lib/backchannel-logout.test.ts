/** @jest-environment node */

import { generateKeyPairSync, sign } from 'node:crypto';
import { validateBackchannelLogout } from './backchannel-logout';

const issuer = 'https://identity.example/realms/waooaw';
const clientId = 'waooaw-web';
const now = 1_800_000_000;
const environment = {
  NODE_ENV: 'test',
  KEYCLOAK_EXPECTED_ISSUER: issuer,
  KEYCLOAK_CLIENT_ID: clientId,
} satisfies NodeJS.ProcessEnv;
const { privateKey, publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
const jwk = { ...publicKey.export({ format: 'jwk' }), kid: 'signing-key', alg: 'RS256', use: 'sig' };

function logoutToken(overrides: Record<string, unknown> = {}) {
  const header = Buffer.from(JSON.stringify({ alg: 'RS256', kid: 'signing-key', typ: 'logout+jwt' })).toString(
    'base64url'
  );
  const payload = Buffer.from(
    JSON.stringify({
      iss: issuer,
      aud: clientId,
      iat: now,
      exp: now + 300,
      jti: 'logout-event-1',
      sid: 'provider-session-1',
      events: { 'http://schemas.openid.net/event/backchannel-logout': {} },
      ...overrides,
    })
  ).toString('base64url');
  const signature = sign('RSA-SHA256', Buffer.from(`${header}.${payload}`), privateKey).toString('base64url');
  return `${header}.${payload}.${signature}`;
}

beforeEach(() => {
  jest.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ keys: [jwk] }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    })
  );
});

afterEach(() => jest.restoreAllMocks());

it('validates exact issuer, client, signature, event, replay id, and sid', async () => {
  await expect(validateBackchannelLogout(logoutToken(), environment, now)).resolves.toMatchObject({
    issuer,
    clientId,
    jti: 'logout-event-1',
    sid: 'provider-session-1',
  });
  expect(fetch).toHaveBeenCalledWith(
    `${issuer}/protocol/openid-connect/certs`,
    expect.objectContaining({ cache: 'no-store' })
  );
});

it.each([
  ['nonce', { nonce: 'forbidden' }],
  ['wrong audience', { aud: 'other-client' }],
  ['ambiguous subject', { sub: 'subject-1' }],
  ['stale token', { iat: now - 301 }],
])('rejects %s logout claims', async (_name, overrides) => {
  await expect(validateBackchannelLogout(logoutToken(overrides), environment, now)).rejects.toThrow();
});
