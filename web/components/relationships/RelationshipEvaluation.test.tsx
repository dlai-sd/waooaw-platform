// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R010
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { render, screen } from '@testing-library/react';
import type { RelationshipEvaluationProjection } from '@/lib/api/relationships';
import { RelationshipEvaluation, trialCountdown } from './RelationshipEvaluation';

const day = 86_400_000;
const start = '2026-12-01T00:00:00Z';

describe('trialCountdown', () => {
  it('counts the real days left from the trial dates, not a fixed length', () => {
    const now = Date.parse(start) + 3 * day + 1;
    expect(trialCountdown(start, '2026-12-15T00:00:00Z', now)).toMatchObject({
      totalDays: 14,
      daysLeft: 11,
      ended: false,
    });
    expect(trialCountdown(start, '2026-12-08T00:00:00Z', now)).toMatchObject({
      totalDays: 7,
      daysLeft: 4,
      ended: false,
    });
  });

  it('says the trial has ended and never goes below zero', () => {
    const now = Date.parse('2026-12-20T00:00:00Z');
    expect(trialCountdown(start, '2026-12-15T00:00:00Z', now)).toMatchObject({ daysLeft: 0, ended: true });
  });
});

describe('RelationshipEvaluation trial', () => {
  const evaluation = (trial: RelationshipEvaluationProjection['trial']) =>
    ({
      relationshipId: 'r1',
      lifecycleState: 'TRIAL_ACTIVE',
      interviewState: 'COMPLETE',
      context: [],
      goals: [],
      skills: [],
      trial,
    }) as unknown as RelationshipEvaluationProjection;

  it('shows the length of this trial and its end date', () => {
    render(
      <RelationshipEvaluation
        evaluation={evaluation({
          trialId: 't1',
          startsAt: new Date(Date.now() - day).toISOString(),
          expiresAt: new Date(Date.now() + 6 * day).toISOString(),
          status: 'ACTIVE',
        } as RelationshipEvaluationProjection['trial'])}
      />
    );
    expect(screen.getByText('7-day demonstration', { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/days left/)).toBeInTheDocument();
    expect(screen.queryByText(/of 14/)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Connections' })).toHaveAttribute('href', '/connections');
    expect(screen.getByText(/practice mode/)).toBeInTheDocument();
  });

  it('offers a one-step Hire when the trial has ended', () => {
    render(
      <RelationshipEvaluation
        evaluation={evaluation({
          trialId: 't1',
          startsAt: new Date(Date.now() - 15 * day).toISOString(),
          expiresAt: new Date(Date.now() - day).toISOString(),
          status: 'EXPIRED',
        } as RelationshipEvaluationProjection['trial'])}
      />
    );
    expect(screen.getByText('Your trial has ended')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Hire your agent to keep it working' })).toHaveAttribute(
      'href',
      '/marketplace'
    );
  });
});
