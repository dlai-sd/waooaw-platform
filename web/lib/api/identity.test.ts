jest.mock('server-only', () => ({}));

import { IdentityApi } from '@/lib/api/generated/apis/IdentityApi';
import { listIdentityProviders } from './identity';

describe('identity provider projection', () => {
  afterEach(() => jest.restoreAllMocks());

  it('returns the Business Platform readiness projection', async () => {
    jest.spyOn(IdentityApi.prototype, 'listIdentityProviders').mockResolvedValue({ providers: [
      { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'AVAILABLE' },
    ] });

    await expect(listIdentityProviders()).resolves.toEqual([
      expect.objectContaining({ id: 'GOOGLE', availability: 'AVAILABLE' }),
    ]);
  });

  it('fails closed when readiness cannot be obtained', async () => {
    jest.spyOn(IdentityApi.prototype, 'listIdentityProviders').mockRejectedValue(new Error('unavailable'));

    const providers = await listIdentityProviders();

    expect(providers).toHaveLength(4);
    expect(providers.every((provider) => provider.availability === 'UNAVAILABLE')).toBe(true);
  });
});