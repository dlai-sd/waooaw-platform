import { render, screen } from '@testing-library/react';
import MarketplaceOfferPage from '@/app/(application)/marketplace/[slug]/page';
import { resolveHireQuote } from '@/lib/api/hire-quote';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { getServerAccessToken } from '@/lib/server-auth';

jest.mock('next/navigation', () => ({ notFound: jest.fn() }));
jest.mock('@/components/acquisition/DisclosureContinuation', () => ({
  DisclosureContinuation: (props: object) => <output data-testid="continuation">{JSON.stringify(props)}</output>,
}));
jest.mock('@/lib/api/professionals', () => ({ getProfessionalDisclosure: jest.fn() }));
jest.mock('@/lib/api/hire-quote', () => ({ resolveHireQuote: jest.fn() }));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));

const quote = {
  packageCode: 'STARTER',
  currency: 'INR',
  grossAmountInrPaise: 354000,
  gstAmountInrPaise: 54000,
  basePriceInrPaise: 300000,
  cadence: 'MONTHLY',
  billingPeriodDays: 30,
  quoteVersion: 'e'.repeat(64),
};

const disclosure = {
  professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
  projectionVersion: '1.0.0',
  customerRouteSlug: 'digital-marketing',
  disclosureRevision: '1.0.0',
  termsVersion: '2026-07-18',
  displayName: 'Digital Marketing Professional',
  suitability: ['Build an evidence-backed marketing plan.', 'Connect activity to business outcomes.'],
  eligibility: { eligible: true, explanation: 'Eligible' },
  skills: [{ skillId: 'MARKET_RESEARCH', displayName: 'Market Research', applicableInTrial: true }],
  limitations: ['No result guarantee'],
  authorityNeeds: ['Approval before publishing'],
  customerRights: ['Stop at any time'],
  trial: { available: true, durationDays: 14, paidApiCallsAllowed: false, externalActionsAllowed: false },
  evidencePosture: 'Evidence-backed',
};

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getProfessionalDisclosure).mockResolvedValue(disclosure);
  jest.mocked(getServerAccessToken).mockResolvedValue('visitor-access-token');
  jest.mocked(resolveHireQuote).mockResolvedValue({ kind: 'quote', quote });
});

const offerPage = async (intent: string) =>
  MarketplaceOfferPage({
    params: Promise.resolve({ slug: 'digital-marketing' }),
    searchParams: Promise.resolve({ professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE', version: '1.0.0', intent }),
  });

it.each([
  ['trial', 'You chose to start a trial.', 'No paid tools'],
  ['hire', 'You chose to hire this professional.', '₹3,540.00'],
])('keeps the %s decision inside Marketplace with authoritative offer facts', async (intent, decision, price) => {
  render(await offerPage(intent));

  expect(screen.getByRole('link', { name: 'Marketplace' })).toHaveAttribute('href', '/marketplace');
  expect(screen.getByRole('heading', { name: 'Digital Marketing Professional' })).toBeVisible();
  expect(screen.getByText(decision)).toBeVisible();
  expect(screen.getByText(price)).toBeVisible();
  expect(screen.getByText('Market Research')).toBeVisible();
  expect(screen.getByTestId('continuation')).toHaveTextContent(`"initialIntent":"${intent}"`);
});

it('hands the server-resolved package and quote version, not an amount of its own, to the Hire continuation', async () => {
  render(await offerPage('hire'));

  expect(resolveHireQuote).toHaveBeenCalledWith('visitor-access-token', 'DIGITAL_MARKETING_LOCAL_SERVICE', '1.0.0');
  const props = JSON.parse(screen.getByTestId('continuation').textContent ?? '{}');
  expect(props).toMatchObject({ packageCode: 'STARTER', quoteVersion: quote.quoteVersion, priceInrPaise: 354000 });
  expect(props.hireUnavailable).toBe(false);
});

it.each([
  ['no package is for sale', { kind: 'not-offered' }],
  ['the billing owner is unavailable', { kind: 'unavailable' }],
])('shows no amount and blocks the Hire when %s', async (_name, outcome) => {
  jest.mocked(resolveHireQuote).mockResolvedValue(outcome as never);

  render(await offerPage('hire'));

  expect(screen.getByText('Price not available right now')).toBeVisible();
  expect(screen.queryByText(/₹/)).not.toBeInTheDocument();
  expect(JSON.parse(screen.getByTestId('continuation').textContent ?? '{}')).toMatchObject({ hireUnavailable: true });
});

it('does not resolve a Hire price for a Trial decision', async () => {
  render(await offerPage('trial'));

  expect(resolveHireQuote).not.toHaveBeenCalled();
});
