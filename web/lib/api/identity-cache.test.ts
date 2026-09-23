jest.mock('server-only', () => ({}));
jest.mock('react', () => ({
  ...jest.requireActual('react'),
  cache: <Arguments extends unknown[], Result>(operation: (...args: Arguments) => Result) => {
    const results = new Map<string, Result>();
    return (...args: Arguments) => {
      const key = JSON.stringify(args);
      if (!results.has(key)) results.set(key, operation(...args));
      return results.get(key) as Result;
    };
  },
}));

import { IdentityApi } from '@/lib/api/generated/apis/IdentityApi';
import { getIdentitySession } from './identity';

it('deduplicates identical session resolution within one server render cache', async () => {
  const session = {
    expiresAt: new Date('2099-09-08T09:00:00Z'),
  } as never;
  const projection = jest.spyOn(IdentityApi.prototype, 'getIdentitySession').mockResolvedValue(session);

  const [layoutIdentity, pageIdentity] = await Promise.all([
    getIdentitySession('shared-render-access-token'),
    getIdentitySession('shared-render-access-token'),
  ]);

  expect(layoutIdentity).toEqual({ kind: 'ready', session });
  expect(pageIdentity).toBe(layoutIdentity);
  expect(projection).toHaveBeenCalledTimes(1);
});