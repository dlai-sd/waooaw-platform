/** @jest-environment node */

const mockStoredEnvelopes: Buffer[] = [];
const mockSql = jest.fn(async (strings: TemplateStringsArray, ...values: unknown[]) => {
  const statement = strings.join('?');
  if (statement.includes('web_session.create_session')) {
    // Digests are 32-byte HMACs; the encrypted token envelope is the only other buffer argument.
    const envelope = values.find((value): value is Buffer => Buffer.isBuffer(value) && value.length !== 32);
    if (!envelope) throw new Error('create_session received no token envelope');
    mockStoredEnvelopes.push(envelope);
    return [];
  }
  if (statement.includes('web_session.lookup_session')) {
    return [
      {
        token_envelope_key_version: 'v1',
        token_envelope: mockStoredEnvelopes[mockStoredEnvelopes.length - 1],
        family_id: '00000000-0000-4000-8000-000000000001',
        handle_id: '00000000-0000-4000-8000-000000000002',
        global_user_id: '00000000-0000-4000-8000-000000000003',
        refresh_version: 0,
        authenticated_at: new Date(),
        absolute_expires_at: new Date(Date.now() + 3_600_000),
        active_membership_id: null,
      },
    ];
  }
  throw new Error(`unexpected statement ${statement}`);
});

jest.mock('postgres', () => ({
  __esModule: true,
  default: jest.fn(() => mockSql),
}));

import { createSession, loadSession } from '@/lib/web-session-store';

describe('Server-session preview deployment binding', () => {
  beforeEach(() => {
    mockStoredEnvelopes.length = 0;
    const key = Buffer.alloc(32, 7).toString('base64');
    process.env.WEB_SESSION_DATABASE_URL = 'postgres://session-test@postgres/waooaw';
    process.env.SESSION_HANDLE_DIGEST_KEYS = JSON.stringify({ v1: key });
    process.env.SESSION_PROTOCOL_DIGEST_KEYS = JSON.stringify({ v1: key });
    process.env.SESSION_TOKEN_ENVELOPE_KEYS = JSON.stringify({ v1: key });
    process.env.SESSION_HANDLE_DIGEST_WRITE_VERSION = 'v1';
    process.env.SESSION_PROTOCOL_DIGEST_WRITE_VERSION = 'v1';
    process.env.SESSION_TOKEN_ENVELOPE_WRITE_VERSION = 'v1';
  });

  it('restores the preview deployment binding so enforced sessions stay authenticated', async () => {
    const created = await createSession(
      {
        accessToken: 'access-token',
        accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 300,
        founder: false,
        previewDeploymentId: 'preview-deployment-1',
      },
      { iss: 'https://identity.example/realms/waooaw', sub: 'subject-1' },
      '00000000-0000-4000-8000-000000000003'
    );

    const loaded = await loadSession(String(created.sessionHandle));

    expect(loaded?.accessToken).toBe('access-token');
    expect(loaded?.previewDeploymentId).toBe('preview-deployment-1');
  });
});
