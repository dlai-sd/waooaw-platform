import LoginPage from '@/app/(auth)/login/page';
import { LoginView } from '@/components/auth/LoginView';
import { redirect } from 'next/navigation';

jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/components/auth/LoginView', () => ({ LoginView: jest.fn(() => null) }));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(redirect).mockImplementation(() => {
    throw new Error('NEXT_REDIRECT');
  });
});

it('returns a completed normal logout to the public homepage', async () => {
  await expect(
    LoginPage({
      searchParams: Promise.resolve({ state: 'waooaw-home-after-logout' }),
    })
  ).rejects.toThrow('NEXT_REDIRECT');

  expect(redirect).toHaveBeenCalledWith('/');
  expect(LoginView).not.toHaveBeenCalled();
});

it('keeps account switching and ordinary visits on the login page', async () => {
  await LoginPage({ searchParams: Promise.resolve({}) });

  expect(redirect).not.toHaveBeenCalled();
  expect(LoginView).not.toHaveBeenCalled();
});

it.each(['GOOGLE', 'FACEBOOK'] as const)(
  'returns a completed %s registration reset to the selected provider',
  async (provider) => {
    await expect(
      LoginPage({
        searchParams: Promise.resolve({ state: `waooaw-register-after-logout:${provider}` }),
      })
    ).rejects.toThrow('NEXT_REDIRECT');

    expect(redirect).toHaveBeenCalledWith(`/register?sessionReset=1&provider=${provider}`);
    expect(LoginView).not.toHaveBeenCalled();
  }
);

it('does not trust an unsupported registration reset state', async () => {
  await LoginPage({
    searchParams: Promise.resolve({ state: 'waooaw-register-after-logout:EMAIL' }),
  });

  expect(redirect).not.toHaveBeenCalled();
});
