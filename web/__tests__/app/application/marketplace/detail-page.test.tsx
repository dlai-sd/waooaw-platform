import { render, screen } from '@testing-library/react';
import MarketplaceOfferPage from '@/app/(application)/marketplace/[slug]/page';
import { getProfessionalDisclosure } from '@/lib/api/professionals';

jest.mock('next/navigation', () => ({ notFound: jest.fn() }));
jest.mock('@/components/acquisition/DisclosureContinuation', () => ({
  DisclosureContinuation: (props: object) => <output data-testid="continuation">{JSON.stringify(props)}</output>,
}));
jest.mock('@/lib/api/professionals', () => ({ getProfessionalDisclosure: jest.fn() }));

const disclosure = {
  professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE', projectionVersion: '1.0.0',
  customerRouteSlug: 'digital-marketing', disclosureRevision: '1.0.0', termsVersion: '2026-07-18',
  displayName: 'Digital Marketing Professional',
  suitability: ['Build an evidence-backed marketing plan.', 'Connect activity to business outcomes.'],
  eligibility: { eligible: true, explanation: 'Eligible' },
  skills: [{ skillId: 'MARKET_RESEARCH', displayName: 'Market Research', applicableInTrial: true }],
  limitations: ['No result guarantee'], authorityNeeds: ['Approval before publishing'], customerRights: ['Stop at any time'],
  trial: { available: true, durationDays: 14, paidApiCallsAllowed: false, externalActionsAllowed: false },
  evidencePosture: 'Evidence-backed',
  indicativePrice: { currency: 'INR', amountInrPaise: 249900, cadence: 'MONTHLY', qualification: 'Indicative' },
};

beforeEach(() => jest.mocked(getProfessionalDisclosure).mockResolvedValue(disclosure));

it.each([['trial', 'You chose to start a trial.', 'No paid tools'], ['hire', 'You chose to hire this professional.', '₹2,499.00']])(
  'keeps the %s decision inside Marketplace with authoritative offer facts', async (intent, decision, price) => {
    render(await MarketplaceOfferPage({
      params: Promise.resolve({ slug: 'digital-marketing' }),
      searchParams: Promise.resolve({ professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE', version: '1.0.0', intent }),
    }));

    expect(screen.getByRole('link', { name: 'Marketplace' })).toHaveAttribute('href', '/marketplace');
    expect(screen.getByRole('heading', { name: 'Digital Marketing Professional' })).toBeVisible();
    expect(screen.getByText(decision)).toBeVisible();
    expect(screen.getByText(price)).toBeVisible();
    expect(screen.getByText('Market Research')).toBeVisible();
    expect(screen.getByTestId('continuation')).toHaveTextContent(`"initialIntent":"${intent}"`);
  },
);