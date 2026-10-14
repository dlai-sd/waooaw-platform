import type { JWT } from 'next-auth/jwt';
import type { IdentityProviderLinkOperationV1 } from '@/lib/api/generated/models/IdentityProviderLinkOperationV1';
import { createIdentityApi } from '@/lib/api/identity';
import { enforceAuthorityChangeRevocation } from '@/lib/identity-lifecycle';
import { revokeAllSessions } from '@/lib/web-session-store';

jest.mock('@/lib/api/identity', () => ({ createIdentityApi: jest.fn() }));
jest.mock('@/lib/web-session-store', () => ({ revokeAllSessions: jest.fn() }));

const operation: IdentityProviderLinkOperationV1 = {
  schemaVersion: '1.0',
  operationReference: '11111111-1111-4111-8111-111111111111',
  linkReference: '22222222-2222-4222-8222-222222222222',
  command: 'LINK',
  provider: 'GOOGLE',
  state: 'COMPLETED',
  expiresAt: new Date('2026-10-14T15:20:00Z'),
  replayed: false,
};
const token = {
  globalUserId: '33333333-3333-4333-8333-333333333333',
} as JWT;

describe('identity lifecycle revocation dominance', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(revokeAllSessions).mockResolvedValue(2);
    jest.mocked(createIdentityApi).mockReturnValue({
      createIdentitySessionRevocation: jest.fn().mockResolvedValue({
        state: 'RECORDED',
      }),
    } as never);
  });

  it('revokes Web authority before recording a terminal lifecycle receipt', async () => {
    const api = createIdentityApi('server-access-token');
    jest.mocked(createIdentityApi).mockReturnValue(api);

    await expect(
      enforceAuthorityChangeRevocation(operation, token, 'server-access-token', '44444444-4444-4444-8444-444444444444')
    ).resolves.toBe(true);

    expect(revokeAllSessions).toHaveBeenCalledWith(token, 'IDENTITY_LINK');
    expect(api.createIdentitySessionRevocation).toHaveBeenCalledWith(
      {
        idempotencyKey: '44444444-4444-4444-8444-444444444444',
        identitySessionRevocationRequestV1: {
          schemaVersion: '1.0',
          scope: 'ALL',
          reason: 'SECURITY_EVENT',
          correlationId: operation.operationReference,
        },
      },
      { cache: 'no-store' }
    );
    expect(jest.mocked(revokeAllSessions).mock.invocationCallOrder[0]).toBeLessThan(
      jest.mocked(api.createIdentitySessionRevocation).mock.invocationCallOrder[0]
    );
  });

  it('does not revoke for a nonterminal operation', async () => {
    await expect(
      enforceAuthorityChangeRevocation(
        { ...operation, state: 'PROOF_REQUIRED' },
        token,
        'server-access-token',
        '44444444-4444-4444-8444-444444444444'
      )
    ).resolves.toBe(false);
    expect(revokeAllSessions).not.toHaveBeenCalled();
  });

  it('does not convert evidence failure into success after revocation', async () => {
    const api = createIdentityApi('server-access-token');
    jest.mocked(api.createIdentitySessionRevocation).mockRejectedValueOnce(new Error('evidence unavailable'));
    jest.mocked(createIdentityApi).mockReturnValue(api);

    await expect(
      enforceAuthorityChangeRevocation(operation, token, 'server-access-token', '44444444-4444-4444-8444-444444444444')
    ).rejects.toThrow('evidence unavailable');
    expect(revokeAllSessions).toHaveBeenCalledTimes(1);
  });
});
