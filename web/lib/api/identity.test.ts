jest.mock('server-only', () => ({}));

import { IdentityApi } from '@/lib/api/generated/apis/IdentityApi';
import { ResponseError } from '@/lib/api/generated/runtime';
import { getIdentitySession, listIdentityProviders } from './identity';

const session = {
  accountReference: 'account-ref',
  roles: new Set(['OWNER'] as const),
  capabilities: new Set(['READ_ACCOUNT'] as const),
  assuranceLevel: 'AAL2_ACCOUNT' as const,
  authenticationPath: 'PORTAL' as const,
  emailVerified: true,
  mobileVerified: false,
  authenticatedAt: new Date('2026-09-08T08:00:00Z'),
  expiresAt: new Date('2099-09-08T09:00:00Z'),
  nextAction: 'NONE' as const,
};

describe('identity provider projection', () => {
  afterEach(() => jest.restoreAllMocks());

  it('returns the Business Platform readiness projection', async () => {
    const projection = jest.spyOn(IdentityApi.prototype, 'listIdentityProviders').mockResolvedValue({ providers: [
      { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'AVAILABLE' },
    ] });

    await expect(listIdentityProviders()).resolves.toEqual([
      expect.objectContaining({ id: 'GOOGLE', availability: 'AVAILABLE' }),
    ]);
    expect(projection).toHaveBeenCalledWith(expect.objectContaining({ cache: 'no-store' }));
  });

  it('fails closed when readiness cannot be obtained', async () => {
    jest.spyOn(IdentityApi.prototype, 'listIdentityProviders').mockRejectedValue(new Error('unavailable'));

    const providers = await listIdentityProviders();

    expect(providers).toHaveLength(4);
    expect(providers.every((provider) => provider.availability === 'UNAVAILABLE')).toBe(true);
  });

  it('returns the current BP-owned session projection without caching', async () => {
    const projection = jest.spyOn(IdentityApi.prototype, 'getIdentitySession').mockResolvedValue(session);

    await expect(getIdentitySession('access-token')).resolves.toEqual({ kind: 'ready', session });
    expect(projection).toHaveBeenCalledWith({ cache: 'no-store' });
  });

  it.each([
    [401, 'unauthorized'],
    [403, 'step-up'],
    [503, 'unavailable'],
  ] as const)('maps HTTP %s to a truthful %s state', async (status, kind) => {
    jest.spyOn(IdentityApi.prototype, 'getIdentitySession').mockRejectedValue(
      new ResponseError({ status } as Response),
    );

    await expect(getIdentitySession('access-token')).resolves.toEqual({ kind });
  });

  it('does not treat an expired projection as an active session', async () => {
    jest.spyOn(IdentityApi.prototype, 'getIdentitySession').mockResolvedValue({
      ...session,
      expiresAt: new Date('2020-01-01T00:00:00Z'),
    });

    await expect(getIdentitySession('access-token')).resolves.toEqual({ kind: 'expired' });
  });
});