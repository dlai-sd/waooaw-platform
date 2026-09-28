import { render, screen } from '@testing-library/react';
import { RelationshipPreActivation } from './RelationshipPreActivation';
import type { EmploymentRelationship, RelationshipEvaluationProjection } from '@/lib/api/relationships';

const relationship: EmploymentRelationship = {
  relationshipId: '77699132-98cf-4cb2-b53d-6a2e1f0c7f92',
  agentInstanceId: '28a4536e-0413-4d64-ae7c-04ac7efd9ff1',
  professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
  professionalVersion: '1.0.0',
  agentInstanceMintedAt: new Date('2026-09-09T10:00:00Z'),
  state: 'CONFIGURING',
  stateVersion: 2,
  createdAt: new Date('2026-09-09T10:00:00Z'),
  updatedAt: new Date('2026-09-09T10:05:00Z'),
};

const evaluation: RelationshipEvaluationProjection = {
  relationshipId: relationship.relationshipId,
  lifecycleState: 'CONFIGURING',
  interviewState: 'COMPLETE',
  context: [],
  goals: [],
  skills: [],
};

describe('RelationshipPreActivation', () => {
  it('collects explicit Hire setup before contract or payment', () => {
    render(
      <RelationshipPreActivation
        relationship={relationship}
        relationships={[]}
        timeline={[]}
        evaluation={evaluation}
        contractJourney={null}
        availableSkills={[
          { skillId: 'MARKET_RESEARCH', displayName: 'Market Research' },
          { skillId: 'CONTENT_STRATEGY', displayName: 'Content Strategy' },
        ]}
      />
    );

    expect(screen.getByRole('heading', { name: 'Configure the professional' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Market Research' })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: /I confirm this budget and scope/ })).not.toBeChecked();
    expect(screen.getByRole('button', { name: 'Prepare exact contract' })).toBeEnabled();
  });
});
