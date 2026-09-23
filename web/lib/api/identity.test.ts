jest.mock('server-only', () => ({}));
jest.mock('react', () => ({
  ...jest.requireActual('react'),
  cache: <Arguments extends unknown[], Result>(operation: (...args: Arguments) => Result) => operation,
}));

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
  beforeEach(() => jest.spyOn(console, 'warn').mockImplementation(() => undefined));
  afterEach(() => jest.restoreAllMocks());

  it('returns the Business Platform readiness projection', async () => {
    const projection = jest.spyOn(IdentityApi.prototype, 'listIdentityProviders').mockResolvedValue({
      providers: [{ id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'AVAILABLE' }],
    });

    await expect(listIdentityProviders()).resolves.toEqual([
      expect.objectContaining({ id: 'GOOGLE', availability: 'AVAILABLE' }),
    ]);
    expect(projection).toHaveBeenCalledWith(expect.objectContaining({ cache: 'no-store' }));
  });

  it('fails closed when readiness cannot be obtained', async () => {
    const projection = jest
      .spyOn(IdentityApi.prototype, 'listIdentityProviders')
      .mockRejectedValue(new Error('unavailable'));

    const providers = await listIdentityProviders();

    expect(projection).toHaveBeenCalledTimes(2);
    expect(providers).toHaveLength(4);
    expect(providers.every((provider) => provider.availability === 'UNAVAILABLE')).toBe(true);
    expect(console.warn).toHaveBeenCalledTimes(2);
  });

  it('recovers when the provider projection becomes available after a transient failure', async () => {
    const projection = jest
      .spyOn(IdentityApi.prototype, 'listIdentityProviders')
      .mockRejectedValueOnce(new Error('cold start'))
      .mockResolvedValueOnce({
        providers: [
          { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'AVAILABLE' },
          { id: 'FACEBOOK', displayName: 'Facebook', authenticationPath: 'META', availability: 'AVAILABLE' },
        ],
      });

    await expect(listIdentityProviders()).resolves.toEqual([
      expect.objectContaining({ id: 'GOOGLE', availability: 'AVAILABLE' }),
      expect.objectContaining({ id: 'FACEBOOK', availability: 'AVAILABLE' }),
    ]);
    expect(projection).toHaveBeenCalledTimes(2);
  });

  it('returns the current BP-owned session projection without caching', async () => {
    const projection = jest.spyOn(IdentityApi.prototype, 'getIdentitySession').mockResolvedValue(session);

    await expect(getIdentitySession('access-token')).resolves.toEqual({ kind: 'ready', session });
    expect(projection).toHaveBeenCalledWith({ cache: 'no-store' });
  });

  it.each([
    [401, 'unauthorized'],
    [503, 'unavailable'],
  ] as const)('maps HTTP %s to a truthful %s state', async (status, kind) => {
    jest
      .spyOn(IdentityApi.prototype, 'getIdentitySession')
      .mockRejectedValue(new ResponseError({ status } as Response));

    await expect(getIdentitySession('access-token')).resolves.toEqual({ kind });
  });

  it.each([
    ['IDENTITY_STEP_UP_REQUIRED', 'step-up'],
    ['IDENTITY_ACTION_DENIED', 'forbidden'],
    ['IDENTITY_DUPLICATE_RESOLUTION_REQUIRED', 'forbidden'],
    ['IDENTITY_VERIFICATION_REQUIRED', 'forbidden'],
  ] as const)('maps typed 403 code %s to %s', async (code, kind) => {
    jest.spyOn(IdentityApi.prototype, 'getIdentitySession').mockRejectedValue(
      new ResponseError({
        status: 403,
        clone: () => ({
          json: async () => ({ code, correlationId: 'd8f914cf-f258-46f3-a41a-e345d489862a' }),
        }),
      } as Response)
    );

    const result = await getIdentitySession(`access-token-${code}`);

    expect(result).toMatchObject({
      kind,
      correlationId: 'd8f914cf-f258-46f3-a41a-e345d489862a',
    });
    if (kind === 'forbidden') expect(result).toMatchObject({ code });
  });

  it('fails an untyped 403 closed as action denied rather than step-up', async () => {
    jest.spyOn(IdentityApi.prototype, 'getIdentitySession').mockRejectedValue(
      new ResponseError({
        status: 403,
        clone: () => ({ json: async () => undefined }),
      } as Response)
    );

    await expect(getIdentitySession('access-token-untyped-denial')).resolves.toEqual({
      kind: 'forbidden',
      code: 'IDENTITY_ACTION_DENIED',
    });
  });

  it('maps only the typed registration-required conflict', async () => {
    jest.spyOn(IdentityApi.prototype, 'getIdentitySession').mockRejectedValue(
      new ResponseError({
        status: 409,
        clone: () => ({ json: async () => ({ code: 'REGISTRATION_REQUIRED' }) }),
      } as Response)
    );

    await expect(getIdentitySession('access-token')).resolves.toEqual({ kind: 'registration-required' });
  });

  it('does not treat an expired projection as an active session', async () => {
    jest.spyOn(IdentityApi.prototype, 'getIdentitySession').mockResolvedValue({
      ...session,
      expiresAt: new Date('2020-01-01T00:00:00Z'),
    });

    await expect(getIdentitySession('access-token')).resolves.toEqual({ kind: 'expired' });
  });
});
