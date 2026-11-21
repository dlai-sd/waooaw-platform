// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063, C-065

import FounderLayout from '@/app/(founder)/layout';
import FounderAccessPage from '@/app/(founder)/founder/access/page';
import RequestAccessPage from '@/app/(application)/access/page';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken } from '@/lib/server-auth';
import { render, screen } from '@testing-library/react';
import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';

jest.mock('next-auth', () => ({ getServerSession: jest.fn() }));
jest.mock('next/navigation', () => ({ redirect: jest.fn() }));
jest.mock('@/lib/auth', () => ({ authOptions: {} }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn(async () => ({ locale: 'en', messages: {} })) }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/lib/platform-access-server', () => ({ resolvePlatformAccess: jest.fn() }));
jest.mock('@/components/shell/ProtectedAppShell', () => ({
  ProtectedAppShell: ({ children }: { children: React.ReactNode }) => <div data-testid="shell">{children}</div>,
}));
jest.mock('@/components/admin/access/AccessApprovals', () => ({ AccessApprovals: () => <p>approvals</p> }));
jest.mock('@/components/admin/access/RequestAccessPanel', () => ({
  RequestAccessPanel: ({ access }: { access: { email: string } }) => <p>request for {access.email}</p>,
}));

const noAccess = {
  founder: false,
  administrator: false,
  emailVerified: true,
  email: 'a@x.com',
  requestableRoles: [],
  requests: [],
};

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getServerSession).mockResolvedValue({ authenticated: true } as never);
  jest.mocked(getServerAccessToken).mockResolvedValue('tok');
  jest.mocked(redirect).mockImplementation(() => {
    throw new Error('NEXT_REDIRECT');
  });
});

describe('founder layout', () => {
  it('sends anonymous visitors to sign in', async () => {
    jest.mocked(getServerSession).mockResolvedValue(null);

    await expect(FounderLayout({ children: <p>secret</p> })).rejects.toThrow('NEXT_REDIRECT');
    expect(redirect).toHaveBeenCalledWith('/login');
  });

  it('refuses a user the Business Platform does not know as the Founder, whatever the token claims', async () => {
    jest.mocked(getServerSession).mockResolvedValue({ authenticated: true, founder: true } as never);
    jest.mocked(resolvePlatformAccess).mockResolvedValue({ ...noAccess, administrator: true });

    await expect(FounderLayout({ children: <p>secret</p> })).rejects.toThrow('NEXT_REDIRECT');
    expect(redirect).toHaveBeenCalledWith('/403');
  });

  it('shows the Founder their pages', async () => {
    jest.mocked(resolvePlatformAccess).mockResolvedValue({ ...noAccess, founder: true, administrator: true });

    render(await FounderLayout({ children: <p>secret</p> }));

    expect(screen.getByText('secret')).toBeVisible();
  });
});

describe('access pages', () => {
  it('shows the Founder the approvals screen', () => {
    render(<FounderAccessPage />);

    expect(screen.getByText('approvals')).toBeVisible();
  });

  it('shows a signed-in user the request screen with what the Business Platform says about them', async () => {
    jest.mocked(resolvePlatformAccess).mockResolvedValue(noAccess);

    render(await RequestAccessPage());

    expect(screen.getByText('request for a@x.com')).toBeVisible();
  });

  it('sends a user without a token home', async () => {
    jest.mocked(getServerAccessToken).mockResolvedValue(undefined);

    await expect(RequestAccessPage()).rejects.toThrow('NEXT_REDIRECT');
    expect(redirect).toHaveBeenCalledWith('/home');
  });
});
