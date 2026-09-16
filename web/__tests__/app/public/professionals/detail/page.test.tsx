import { render, screen } from '@testing-library/react';
import ProfessionalPage from '@/app/(public)/professionals/[slug]/page';
import { getProfessionalDisclosure } from '@/lib/api/professionals';

jest.mock('next/navigation', () => ({ notFound: jest.fn() }));
jest.mock('@/components/public/StructuredData', () => ({ StructuredData: () => null }));
jest.mock('@/components/acquisition/DisclosureContinuation', () => ({ DisclosureContinuation: (props: object) => <output data-testid="continuation">{JSON.stringify(props)}</output> }));
jest.mock('@/lib/api/professionals', () => ({ getProfessionalDisclosure: jest.fn() }));

it.each([
  ['Start trial', 'trial'],
  ['Hire', 'hire'],
])('preserves the professional and %s intent through registration', async (label, intent) => {
  jest.mocked(getProfessionalDisclosure).mockResolvedValue({
    professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE', projectionVersion: '1.0.0',
    customerRouteSlug: 'digital-marketing', disclosureRevision: '1.0.0', termsVersion: '2026-07-18',
    displayName: 'Digital Marketing Professional', suitability: ['Build a local marketing plan'],
    eligibility: { eligible: true, explanation: 'Eligible' },
    skills: [{ skillId: 'MARKET_RESEARCH', displayName: 'Market Research', applicableInTrial: true }],
    limitations: ['No result guarantee'], authorityNeeds: ['Approval before publishing'], customerRights: ['Stop at any time'],
    trial: { available: true, durationDays: 14, paidApiCallsAllowed: false, externalActionsAllowed: false },
    evidencePosture: 'Evidence-backed',
    indicativePrice: { currency: 'INR', amountInrPaise: 249900, cadence: 'MONTHLY', qualification: 'Indicative' },
  });

  render(await ProfessionalPage({
    params: Promise.resolve({ slug: 'digital-marketing' }),
    searchParams: Promise.resolve({ professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE', version: '1.0.0', intent }),
  }));

  expect(screen.getByRole('heading', { name: 'Digital Marketing Professional' })).toBeInTheDocument();
  expect(screen.getByTestId('continuation')).toHaveTextContent('"professionalType":"DIGITAL_MARKETING_LOCAL_SERVICE"');
  expect(screen.getByTestId('continuation')).toHaveTextContent('"professionalVersion":"1.0.0"');
  expect(screen.getByTestId('continuation')).toHaveTextContent(`"initialIntent":"${intent}"`);
});