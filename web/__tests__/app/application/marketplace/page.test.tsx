import { render, screen } from '@testing-library/react';
import MarketplacePage from '@/app/(application)/marketplace/page';
import { browseMarketplaceProfessionals } from '@/lib/api/professionals';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';

jest.mock('@/lib/api/professionals', () => ({ browseMarketplaceProfessionals: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getRequestI18n).mockResolvedValue({
    locale: 'en',
    messages: { returnHome: 'Return home' },
  } as never);
});

it('does not browse Marketplace without an authenticated access token', async () => {
  jest.mocked(getServerAccessToken).mockResolvedValue(undefined);

  render(await MarketplacePage({ searchParams: Promise.resolve({}) }));

  expect(screen.getByRole('heading', { name: 'Marketplace unavailable' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
  expect(browseMarketplaceProfessionals).not.toHaveBeenCalled();
});

it('uses the authenticated visitor token only for the published Marketplace projection', async () => {
  jest.mocked(getServerAccessToken).mockResolvedValue('visitor-access-token');
  jest.mocked(browseMarketplaceProfessionals).mockResolvedValue({
    schemaVersion: '1.0.0',
    producedAt: new Date('2026-09-15T00:00:00Z'),
    items: [],
  });

  render(await MarketplacePage({ searchParams: Promise.resolve({ q: 'marketing' }) }));

  expect(browseMarketplaceProfessionals).toHaveBeenCalledWith('visitor-access-token', { q: 'marketing' });
  expect(screen.getByRole('heading', { name: 'No professionals found' })).toBeInTheDocument();
});

it('uses the canonical disclosure route and preserves each available intent', async () => {
  jest.mocked(getServerAccessToken).mockResolvedValue('visitor-access-token');
  jest.mocked(browseMarketplaceProfessionals).mockResolvedValue({
    schemaVersion: '1.0.0',
    producedAt: new Date('2026-09-15T00:00:00Z'),
    items: [{
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      version: '1.0.0',
      displayName: 'Digital Marketing Agent',
      disclosurePath: '/marketplace/digital-marketing',
      availableIntents: new Set(['TRIAL', 'HIRE']),
      suitability: ['Build an evidence-backed marketing plan.'],
      eligibility: { isEligible: true, explanation: 'Available for your business.' },
      indicativePrice: { currency: 'INR', amountInrPaise: 249900, cadence: 'MONTHLY', qualification: 'Indicative' },
      offerabilityState: 'OFFERABLE',
      trialTerms: '14-day governed trial',
      nextAction: 'VIEW_DISCLOSURE',
    }],
  } as never);

  render(await MarketplacePage({ searchParams: Promise.resolve({}) }));

  expect(screen.getByRole('link', { name: /Start trial/ })).toHaveAttribute(
    'href',
    '/marketplace/digital-marketing?professionalType=DIGITAL_MARKETING_LOCAL_SERVICE&version=1.0.0&intent=trial',
  );
  expect(screen.getByRole('link', { name: /Hire/ })).toHaveAttribute(
    'href',
    '/marketplace/digital-marketing?professionalType=DIGITAL_MARKETING_LOCAL_SERVICE&version=1.0.0&intent=hire',
  );
  expect(document.querySelector('a[href*="digital-marketing-local-service"]')).not.toBeInTheDocument();
  expect(screen.queryByText('DIGITAL_MARKETING_LOCAL_SERVICE')).not.toBeInTheDocument();
  expect(screen.queryByText(/Eligibility depends only/)).not.toBeInTheDocument();
  expect(screen.getByText('Build an evidence-backed marketing plan.')).toBeInTheDocument();
  expect(screen.getByText('14-day governed trial')).toBeInTheDocument();
  expect(screen.queryByRole('search')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument();
});