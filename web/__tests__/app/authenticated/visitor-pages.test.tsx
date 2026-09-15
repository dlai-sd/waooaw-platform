import { render, screen } from '@testing-library/react';
import AlertsPage from '@/app/(authenticated)/alerts/page';
import ProfilePage from '@/app/(authenticated)/profile/page';
import SettingsPage from '@/app/(authenticated)/settings/page';
import { getIdentitySession } from '@/lib/api/identity';
import { getServerAccessToken } from '@/lib/server-auth';

jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/lib/api/identity', () => ({
  getCustomerProfile: jest.fn(),
  getCustomerSettings: jest.fn(),
  getIdentitySession: jest.fn(),
  listCustomerLoginMethods: jest.fn(),
}));
jest.mock('@/lib/api/notifications', () => ({ listCustomerAlerts: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({
  getRequestI18n: async () => ({ locale: 'en', messages: { returnHome: 'Return home' } }),
}));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getServerAccessToken).mockResolvedValue('access-token');
  jest.mocked(getIdentitySession).mockResolvedValue({ kind: 'registration-required' });
});

it.each([
  ['Alerts', AlertsPage, 'No alerts yet'],
  ['Profile', ProfilePage, 'Your customer profile is ready to begin'],
  ['Settings', SettingsPage, 'Customer settings will appear here'],
] as const)('keeps %s available to an authenticated visitor', async (_name, Page, heading) => {
  render(await Page());

  expect(screen.getByRole('heading', { name: heading })).toBeVisible();
  expect(screen.getByRole('link', { name: 'Browse Marketplace' })).toHaveAttribute('href', '/marketplace');
});