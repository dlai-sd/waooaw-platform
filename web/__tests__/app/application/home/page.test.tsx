import { getIdentitySession } from '@/lib/api/identity';
import { listEmploymentRelationships } from '@/lib/api/relationships';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';
import { redirect } from 'next/navigation';
import ApplicationHomePage from '@/app/(application)/home/page';

jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/api/relationships', () => ({ listEmploymentRelationships: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
  jest.mocked(getRequestI18n).mockResolvedValue({ messages: {} } as never);
  jest.mocked(redirect).mockImplementation(() => { throw new Error('NEXT_REDIRECT'); });
});

it('sends an authenticated visitor to Marketplace', async () => {
  jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'registration-required' });

  await expect(ApplicationHomePage()).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/marketplace');
  expect(listEmploymentRelationships).not.toHaveBeenCalled();
});

it('sends a registered customer without relationships to Marketplace', async () => {
  jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'ready', session: {} as never });
  jest.mocked(listEmploymentRelationships).mockResolvedValue({ items: [] } as never);

  await expect(ApplicationHomePage()).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/marketplace');
});

it('sends a registered customer with retained relationships to My Agents', async () => {
  jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'ready', session: {} as never });
  jest.mocked(listEmploymentRelationships).mockResolvedValue({ items: [{ relationshipId: 'relationship-1' }] } as never);

  await expect(ApplicationHomePage()).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/professionals/mine');
});