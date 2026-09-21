import { redirect } from 'next/navigation';
import CustomerLayout from '@/app/(application)/layout';
import { getIdentitySession } from '@/lib/api/identity';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';

jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({ getIdentitySession: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/components/shell/ProtectedAppShell', () => ({
  ProtectedAppShell: ({ children, identitySession }: { children: React.ReactNode; identitySession?: unknown }) => (
    <div data-has-membership={identitySession !== undefined} data-testid="customer-shell">
      {children}
    </div>
  ),
}));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
  jest.mocked(getRequestI18n).mockResolvedValue({ locale: 'en', messages: {} } as never);
  jest.mocked(redirect).mockImplementation(() => {
    throw new Error('NEXT_REDIRECT');
  });
});

it('routes an authenticated visitor without membership through registration', async () => {
  jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'registration-required' });

  await expect(CustomerLayout({ children: <p>My Agents</p> })).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/register?returnTo=%2Fhome');
});
