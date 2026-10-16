import 'server-only';

import { createCipheriv, createDecipheriv, createHmac, randomBytes, randomUUID } from 'node:crypto';
import type { WebManagedSession, WebSessionAssuranceLevel } from '@/lib/web-managed-session';
import type { JWT } from 'next-auth/jwt';
import postgres from 'postgres';

const IDLE_SECONDS = 30 * 60;
const ABSOLUTE_SECONDS = 8 * 60 * 60;
const SESSION_POOL_SIZE = 5;
const POOL_ACQUISITION_TIMEOUT_MS = 1_000;

interface StoredTokenEnvelope {
  accessToken: string;
  accessTokenExpiresAt?: number;
  refreshToken?: string;
  idToken?: string;
  founder: boolean;
}

export interface OidcTransactionEnvelope {
  state: string;
  intent: 'LOGIN' | 'REGISTER' | 'TRIAL' | 'HIRE';
  callbackPath: string;
  protocolCookies: Record<string, string>;
}

interface SessionRow {
  family_id: string;
  handle_id: string;
  global_user_id: string;
  assurance_class: string;
  authenticated_at: Date;
  active_membership_id: string | null;
  token_envelope_key_version: string;
  token_envelope: Uint8Array;
  refresh_version: string;
  idle_expires_at: Date;
  absolute_expires_at: Date;
}

interface OidcTransactionRow {
  transaction_envelope_key_version: string;
  transaction_envelope: Uint8Array;
  provider_class: 'GOOGLE' | 'FACEBOOK' | 'APPLE' | 'EMAIL';
}

interface ManagedSessionRow {
  session_id: string;
  issued_at: Date;
  last_seen_at: Date;
  expires_at: Date;
  assurance_level: string;
  provider: string;
  device_label: string;
  current_session: boolean;
}

function assuranceLevel(value: string): WebSessionAssuranceLevel {
  switch (value) {
    case 'AAL1_CHANNEL':
    case 'AAL2_ACCOUNT':
    case 'AAL3_FRESH':
    case 'AAL4_PAYMENT':
      return value;
    default:
      return 'AAL2_ACCOUNT';
  }
}

function keyring(name: string): Record<string, Buffer> {
  const raw = process.env[name];
  if (!raw) throw new Error(`${name} is required`);
  const parsed = JSON.parse(raw) as Record<string, unknown>;
  const entries = Object.entries(parsed).map(([version, value]) => {
    if (!version || typeof value !== 'string') throw new Error(`${name} is invalid`);
    const key = Buffer.from(value, 'base64');
    if (key.length !== 32) throw new Error(`${name} keys must contain 32 bytes`);
    return [version, key] as const;
  });
  if (entries.length < 1 || entries.length > 2) throw new Error(`${name} must contain one or two keys`);
  return Object.fromEntries(entries);
}

function writeKey(name: string, keys: Record<string, Buffer>): [string, Buffer] {
  const version = process.env[name];
  const key = version && keys[version];
  if (!version || !key) throw new Error(`${name} must select a readable key`);
  return [version, key];
}

function digest(value: string, key: Buffer, domain: string): Buffer {
  return createHmac('sha256', key).update(`${domain}\0${value}`, 'utf8').digest();
}

function encrypt(value: object, key: Buffer): Buffer {
  const nonce = randomBytes(12);
  const cipher = createCipheriv('aes-256-gcm', key, nonce);
  const ciphertext = Buffer.concat([cipher.update(JSON.stringify(value), 'utf8'), cipher.final()]);
  return Buffer.concat([nonce, cipher.getAuthTag(), ciphertext]);
}

function decrypt<T extends object>(value: Uint8Array, key: Buffer): T {
  const encoded = Buffer.from(value);
  if (encoded.length < 29) throw new Error('Token envelope is invalid');
  const decipher = createDecipheriv('aes-256-gcm', key, encoded.subarray(0, 12));
  decipher.setAuthTag(encoded.subarray(12, 28));
  return JSON.parse(Buffer.concat([decipher.update(encoded.subarray(28)), decipher.final()]).toString('utf8')) as T;
}

let client: ReturnType<typeof postgres> | undefined;
let activeDatabaseOperations = 0;
const databaseWaiters: Array<{
  resolve: () => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}> = [];

function database() {
  const url = process.env.WEB_SESSION_DATABASE_URL;
  if (!url) throw new Error('WEB_SESSION_DATABASE_URL is required');
  const sslMode = process.env.WEB_SESSION_DATABASE_SSL_MODE;
  if (sslMode && sslMode !== 'disable' && sslMode !== 'require')
    throw new Error('WEB_SESSION_DATABASE_SSL_MODE must be disable or require');
  client ??= postgres(url, {
    max: SESSION_POOL_SIZE,
    connect_timeout: 3,
    idle_timeout: 30,
    max_lifetime: 300,
    prepare: false,
    ssl:
      sslMode === 'disable'
        ? false
        : sslMode === 'require' || process.env.NODE_ENV === 'production'
          ? 'require'
          : false,
    onnotice: () => {},
  });
  return client;
}

async function acquireDatabaseSlot(): Promise<void> {
  if (activeDatabaseOperations < SESSION_POOL_SIZE) {
    activeDatabaseOperations += 1;
    return;
  }
  await new Promise<void>((resolve, reject) => {
    const waiter = {
      resolve,
      reject,
      timer: setTimeout(() => {
        const index = databaseWaiters.indexOf(waiter);
        if (index >= 0) databaseWaiters.splice(index, 1);
        reject(new Error('Web session database pool acquisition timed out'));
      }, POOL_ACQUISITION_TIMEOUT_MS),
    };
    databaseWaiters.push(waiter);
  });
}

function releaseDatabaseSlot() {
  const waiter = databaseWaiters.shift();
  if (waiter) {
    clearTimeout(waiter.timer);
    waiter.resolve();
    return;
  }
  activeDatabaseOperations -= 1;
}

async function withDatabaseSlot<T>(operation: () => Promise<T>): Promise<T> {
  await acquireDatabaseSlot();
  try {
    return await operation();
  } finally {
    releaseDatabaseSlot();
  }
}

export async function loadSession(handle: string): Promise<JWT | null> {
  if (!/^[A-Za-z0-9_-]{43}$/.test(handle)) return null;
  const handleKeys = keyring('SESSION_HANDLE_DIGEST_KEYS');
  const envelopeKeys = keyring('SESSION_TOKEN_ENVELOPE_KEYS');
  for (const [version, key] of Object.entries(handleKeys)) {
    const rows = await withDatabaseSlot(
      () => database()<SessionRow[]>`
      SELECT *
      FROM web_session.lookup_session(
        ${version},
        ${digest(handle, key, 'session-handle')},
        clock_timestamp()
      )
    `
    );
    const row = rows[0];
    if (!row) continue;
    const envelopeKey = envelopeKeys[row.token_envelope_key_version];
    if (!envelopeKey) throw new Error('Session envelope key version is unavailable');
    const envelope = decrypt<StoredTokenEnvelope>(row.token_envelope, envelopeKey);
    return {
      ...envelope,
      sessionHandle: handle,
      sessionFamilyId: row.family_id,
      sessionHandleId: row.handle_id,
      globalUserId: row.global_user_id,
      refreshVersion: Number(row.refresh_version),
      authenticatedAt: row.authenticated_at.toISOString(),
      sessionAbsoluteExpiresAt: row.absolute_expires_at.toISOString(),
      activeMembershipId: row.active_membership_id ?? undefined,
    };
  }
  return null;
}

export async function createOidcTransaction(
  state: string,
  browserBinding: string,
  providerClass: OidcTransactionRow['provider_class'],
  envelope: OidcTransactionEnvelope
): Promise<void> {
  const protocolKeys = keyring('SESSION_PROTOCOL_DIGEST_KEYS');
  const envelopeKeys = keyring('SESSION_TOKEN_ENVELOPE_KEYS');
  const [protocolVersion, protocolKey] = writeKey('SESSION_PROTOCOL_DIGEST_WRITE_VERSION', protocolKeys);
  const [envelopeVersion, envelopeKey] = writeKey('SESSION_TOKEN_ENVELOPE_WRITE_VERSION', envelopeKeys);
  await withDatabaseSlot(
    () => database()`
      SELECT web_session.create_oidc_transaction(
        ${randomUUID()}::uuid,
        ${protocolVersion},
        ${digest(state, protocolKey, 'oidc-state')},
        ${envelopeVersion},
        ${encrypt(envelope, envelopeKey)},
        ${digest(browserBinding, protocolKey, 'oidc-browser')},
        ${providerClass},
        ${new Date(Date.now() + 10 * 60 * 1000)}
      )
    `
  );
}

export async function consumeOidcTransaction(
  state: string,
  browserBinding: string
): Promise<(OidcTransactionEnvelope & { providerClass: OidcTransactionRow['provider_class'] }) | null> {
  const protocolKeys = keyring('SESSION_PROTOCOL_DIGEST_KEYS');
  const envelopeKeys = keyring('SESSION_TOKEN_ENVELOPE_KEYS');
  for (const [version, key] of Object.entries(protocolKeys)) {
    const rows = await withDatabaseSlot(
      () => database()<OidcTransactionRow[]>`
        SELECT *
        FROM web_session.consume_oidc_transaction(
          ${version},
          ${digest(state, key, 'oidc-state')},
          ${digest(browserBinding, key, 'oidc-browser')},
          clock_timestamp()
        )
      `
    );
    const row = rows[0];
    if (!row) continue;
    const envelopeKey = envelopeKeys[row.transaction_envelope_key_version];
    if (!envelopeKey) throw new Error('OIDC transaction envelope key version is unavailable');
    return {
      ...decrypt<OidcTransactionEnvelope>(row.transaction_envelope, envelopeKey),
      providerClass: row.provider_class,
    };
  }
  return null;
}

export async function createSession(token: JWT, profile: Record<string, unknown>, globalUserId: string): Promise<JWT> {
  const handle = randomBytes(32).toString('base64url');
  const familyId = randomUUID();
  const handleId = randomUUID();
  const handleKeys = keyring('SESSION_HANDLE_DIGEST_KEYS');
  const envelopeKeys = keyring('SESSION_TOKEN_ENVELOPE_KEYS');
  const protocolKeys = keyring('SESSION_PROTOCOL_DIGEST_KEYS');
  const [handleVersion, handleKey] = writeKey('SESSION_HANDLE_DIGEST_WRITE_VERSION', handleKeys);
  const [envelopeVersion, envelopeKey] = writeKey('SESSION_TOKEN_ENVELOPE_WRITE_VERSION', envelopeKeys);
  const [protocolVersion, protocolKey] = writeKey('SESSION_PROTOCOL_DIGEST_WRITE_VERSION', protocolKeys);
  const now = new Date();
  const absoluteExpiresAt = new Date(now.getTime() + ABSOLUTE_SECONDS * 1000);
  const authenticatedAt = new Date(
    (typeof profile.auth_time === 'number' ? profile.auth_time : Math.floor(now.getTime() / 1000)) * 1000
  );
  const issuer = typeof profile.iss === 'string' ? profile.iss : '';
  const subject = typeof profile.sub === 'string' ? profile.sub : '';
  if (!issuer || !subject) throw new Error('Validated issuer and subject are required');
  const sid = typeof profile.sid === 'string' ? profile.sid : undefined;
  const envelope: StoredTokenEnvelope = {
    accessToken: String(token.accessToken),
    accessTokenExpiresAt: token.accessTokenExpiresAt,
    refreshToken: token.refreshToken,
    idToken: token.idToken,
    founder: token.founder === true,
  };
  await withDatabaseSlot(
    () => database()`
    SELECT *
    FROM web_session.create_session(
      ${familyId}::uuid,
      ${handleId}::uuid,
      ${globalUserId}::uuid,
      ${issuer},
      ${subject},
      ${process.env.KEYCLOAK_CLIENT_ID ?? 'waooaw-web'},
      ${typeof profile.acr === 'string' ? profile.acr : 'AAL2'},
      ${authenticatedAt},
      ${sid ? protocolVersion : null},
      ${sid ? digest(sid, protocolKey, 'keycloak-sid') : null},
      ${envelopeVersion},
      ${encrypt(envelope, envelopeKey)},
      ${handleVersion},
      ${digest(handle, handleKey, 'session-handle')},
      ${new Date(now.getTime() + IDLE_SECONDS * 1000)},
      ${absoluteExpiresAt},
      ${process.env.WEB_SESSION_DEPLOY_VERSION ?? 'wc123-auth-session-v1'}
    )
  `
  );
  return {
    ...token,
    sessionHandle: handle,
    sessionFamilyId: familyId,
    sessionHandleId: handleId,
    globalUserId,
    refreshVersion: 0,
    authenticatedAt: authenticatedAt.toISOString(),
    sessionAbsoluteExpiresAt: absoluteExpiresAt.toISOString(),
  };
}

export async function revokeSession(token: JWT, reason: string): Promise<void> {
  const familyId = token.sessionFamilyId;
  if (typeof familyId !== 'string') return;
  await withDatabaseSlot(
    () => database()`
    SELECT web_session.revoke_family(
      ${familyId}::uuid,
      ${reason},
      ${randomUUID()}::uuid
    )
  `
  );
}

export async function revokeAllSessions(token: JWT, reason: string): Promise<number> {
  const globalUserId = token.globalUserId;
  if (typeof globalUserId !== 'string') return 0;
  const rows = await withDatabaseSlot(
    () => database()<[{ revoked_count: string }]>`
    SELECT web_session.revoke_all(
      ${globalUserId}::uuid,
      ${reason},
      ${randomUUID()}::uuid
    ) AS revoked_count
  `
  );
  return Number(rows[0]?.revoked_count ?? 0);
}

export async function listSessions(token: JWT): Promise<WebManagedSession[]> {
  const globalUserId = token.globalUserId;
  const familyId = token.sessionFamilyId;
  if (typeof globalUserId !== 'string' || typeof familyId !== 'string') return [];
  const rows = await withDatabaseSlot(
    () => database()<ManagedSessionRow[]>`
    SELECT *
    FROM web_session.list_sessions(
      ${globalUserId}::uuid,
      ${familyId}::uuid,
      clock_timestamp()
    )
  `
  );
  return rows.map((row) => ({
    sessionId: row.session_id,
    issuedAt: row.issued_at,
    lastSeenAt: row.last_seen_at,
    expiresAt: row.expires_at,
    assuranceLevel: assuranceLevel(row.assurance_level),
    provider: 'UNKNOWN',
    deviceLabel: row.device_label,
    current: row.current_session,
  }));
}

export async function revokeOneSession(token: JWT, sessionId: string): Promise<number> {
  const globalUserId = token.globalUserId;
  if (
    typeof globalUserId !== 'string' ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(sessionId)
  )
    return -1;
  const rows = await withDatabaseSlot(
    () => database()<[{ revoked_count: string }]>`
    SELECT web_session.revoke_one(
      ${globalUserId}::uuid,
      ${sessionId}::uuid,
      ${'CUSTOMER_REVOKED'},
      ${randomUUID()}::uuid
    ) AS revoked_count
  `
  );
  return Number(rows[0]?.revoked_count ?? -1);
}

export async function rotateSessionMembership(token: JWT, activeMembershipId: string): Promise<JWT | null> {
  const familyId = token.sessionFamilyId;
  const previousHandleId = token.sessionHandleId;
  const refreshVersion = token.refreshVersion;
  const absoluteExpiresAt =
    typeof token.sessionAbsoluteExpiresAt === 'string' ? Date.parse(token.sessionAbsoluteExpiresAt) : Number.NaN;
  if (
    typeof familyId !== 'string' ||
    typeof previousHandleId !== 'string' ||
    typeof refreshVersion !== 'number' ||
    !Number.isFinite(absoluteExpiresAt) ||
    absoluteExpiresAt <= Date.now() ||
    !/^[0-9a-f-]{36}$/i.test(activeMembershipId)
  )
    return null;
  const handle = randomBytes(32).toString('base64url');
  const handleId = randomUUID();
  const handleKeys = keyring('SESSION_HANDLE_DIGEST_KEYS');
  const [version, key] = writeKey('SESSION_HANDLE_DIGEST_WRITE_VERSION', handleKeys);
  const rows = await withDatabaseSlot(
    () => database()<[{ rotated: boolean }]>`
    SELECT web_session.rotate_handle(
      ${familyId}::uuid,
      ${refreshVersion},
      ${previousHandleId}::uuid,
      ${handleId}::uuid,
      ${version},
      ${digest(handle, key, 'session-handle')},
      ${new Date(absoluteExpiresAt)},
      ${activeMembershipId}::uuid
    ) AS rotated
  `
  );
  if (!rows[0]?.rotated) return null;
  return {
    ...token,
    sessionHandle: handle,
    sessionHandleId: handleId,
    refreshVersion: refreshVersion + 1,
    activeMembershipId,
  };
}

export async function acquireRefreshLease(token: JWT): Promise<string | null> {
  const familyId = token.sessionFamilyId;
  const refreshVersion = token.refreshVersion;
  if (typeof familyId !== 'string' || typeof refreshVersion !== 'number') return null;
  const owner = randomUUID();
  const rows = await withDatabaseSlot(
    () => database()<[{ acquired: boolean }]>`
    SELECT web_session.acquire_refresh_lease(
      ${familyId}::uuid,
      ${refreshVersion},
      ${owner}::uuid,
      15
    ) AS acquired
  `
  );
  return rows[0]?.acquired ? owner : null;
}

export async function completeRefresh(token: JWT, leaseOwner: string): Promise<boolean> {
  const familyId = token.sessionFamilyId;
  const refreshVersion = token.refreshVersion;
  if (typeof familyId !== 'string' || typeof refreshVersion !== 'number') return false;
  const envelopeKeys = keyring('SESSION_TOKEN_ENVELOPE_KEYS');
  const [version, key] = writeKey('SESSION_TOKEN_ENVELOPE_WRITE_VERSION', envelopeKeys);
  const envelope: StoredTokenEnvelope = {
    accessToken: String(token.accessToken),
    accessTokenExpiresAt: token.accessTokenExpiresAt,
    refreshToken: token.refreshToken,
    idToken: token.idToken,
    founder: token.founder === true,
  };
  const rows = await withDatabaseSlot(
    () => database()<[{ completed: boolean }]>`
    SELECT web_session.complete_refresh(
      ${familyId}::uuid,
      ${refreshVersion},
      ${leaseOwner}::uuid,
      ${version},
      ${encrypt(envelope, key)},
      ${new Date(Date.now() + IDLE_SECONDS * 1000)}
    ) AS completed
  `
  );
  return rows[0]?.completed === true;
}

export async function sessionStoreReady(): Promise<boolean> {
  keyring('SESSION_HANDLE_DIGEST_KEYS');
  keyring('SESSION_PROTOCOL_DIGEST_KEYS');
  keyring('SESSION_TOKEN_ENVELOPE_KEYS');
  const deployVersion = process.env.WEB_SESSION_DEPLOY_VERSION ?? 'wc123-auth-session-v1';
  const rows = await withDatabaseSlot(
    () => database()<[{ ready: boolean }]>`
    SELECT web_session.schema_ready(1, ${deployVersion}) AS ready
  `
  );
  return rows[0]?.ready === true;
}

export async function oidcTransactionStoreReady(): Promise<boolean> {
  keyring('SESSION_PROTOCOL_DIGEST_KEYS');
  keyring('SESSION_TOKEN_ENVELOPE_KEYS');
  const deployVersion = process.env.WEB_SESSION_DEPLOY_VERSION ?? 'wc123-auth-session-v1';
  const rows = await withDatabaseSlot(
    () => database()<[{ ready: boolean }]>`
    SELECT web_session.schema_ready(1, ${deployVersion}) AS ready
  `
  );
  return rows[0]?.ready === true;
}

export async function applyBackchannelLogout(input: {
  issuer: string;
  clientId: string;
  jti: string;
  sid?: string;
  subject?: string;
  issuedAt: Date;
  expiresAt: Date;
}): Promise<'APPLIED' | 'REPLAY'> {
  const protocolKeys = keyring('SESSION_PROTOCOL_DIGEST_KEYS');
  const [version, key] = writeKey('SESSION_PROTOCOL_DIGEST_WRITE_VERSION', protocolKeys);
  const rows = await withDatabaseSlot(
    () => database()<[{ revoked: number }]>`
    SELECT web_session.apply_backchannel_logout(
      ${input.issuer},
      ${input.clientId},
      ${version},
      ${digest(input.jti, key, 'logout-jti')},
      ${input.sid ? digest(input.sid, key, 'keycloak-sid') : null},
      ${input.subject ?? null},
      ${input.issuedAt},
      ${input.expiresAt},
      ${randomUUID()}::uuid
    ) AS revoked
  `
  );
  return rows[0]?.revoked === -1 ? 'REPLAY' : 'APPLIED';
}
