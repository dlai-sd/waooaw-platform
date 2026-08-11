import { fireEvent, render, screen } from '@testing-library/react';
import { ProfessionalComparison } from './ProfessionalComparison';
import type { ProfessionalDisclosure } from '@/lib/api/professionals';

const professional: ProfessionalDisclosure = {
  professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
  projectionVersion: '1.0.0',
  displayName: 'Digital Marketing Professional',
  suitability: ['Local customer growth'],
  eligibility: { eligible: true, explanation: 'Suitable for lawful local growth.' },
  skills: [
    { skillId: 'RESEARCH', displayName: 'Market research', applicableInTrial: true },
    { skillId: 'PUBLISH', displayName: 'Publishing', applicableInTrial: false, activationCondition: 'Requires contract authority' },
  ],
  limitations: ['No guaranteed outcome'],
  authorityNeeds: ['Approval before publishing'],
  customerRights: ['Stop at any time'],
  trial: { available: true, durationDays: 14, paidApiCallsAllowed: false, externalActionsAllowed: false },
  evidencePosture: 'Every claim links to retained evidence.',
  indicativePrice: { currency: 'INR', amountInrPaise: 100000, cadence: 'MONTH', qualification: 'Final price follows configuration.' },
};

describe('ProfessionalComparison', () => {
  it('shows disclosures and boundaries before interview entry', () => {
    render(<ProfessionalComparison professionals={[professional]} />);

    expect(screen.getByText('Digital Marketing Professional')).toBeVisible();
    expect(screen.getByText(/no paid APIs and no external actions/i)).toBeVisible();
    expect(screen.getByText('No guaranteed outcome')).toBeVisible();
    expect(screen.getByText('Stop at any time')).toBeVisible();
    fireEvent.click(screen.getByText('Inspect all 2 skills'));
    expect(screen.getByText('Requires contract authority')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Interview this professional' })).toHaveAttribute(
      'href',
      '/login?professional=DIGITAL_MARKETING_LOCAL_SERVICE',
    );
  });

  it('does not invent a match when discovery returns none', () => {
    render(<ProfessionalComparison professionals={[]} />);

    expect(screen.getByText(/No suitable professional was found/i)).toBeVisible();
  });
});