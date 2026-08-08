import { render, screen } from '@testing-library/react';
import { RelationshipWorkspace } from './RelationshipWorkspace';
import type { EmploymentRelationship, RelationshipTimelineEntry } from '@/lib/api/relationships';

const relationship: EmploymentRelationship = {
  relationshipId: '5f33925b-fb0c-4366-8414-7f85309639b9',
  professionalType: 'DIGITAL_MARKETING',
  state: 'TRIAL_ACTIVE',
  stateVersion: 1,
  createdAt: new Date('2026-08-08T10:00:00Z'),
  updatedAt: new Date('2026-08-08T10:05:00Z'),
};

const timeline: RelationshipTimelineEntry[] = [{
  stateVersion: 1,
  fromState: 'INTERVIEWING',
  toState: 'TRIAL_ACTIVE',
  actorParticipantId: '2766ab1e-3778-413c-acf6-521506219d49',
  actorRole: 'EVALUATOR',
  correlationId: '40ef2b54-c6e4-4ca4-826e-8900f394f299',
  evidenceId: '2af901e4-e0db-49a6-bfcc-bb8e575159f2',
  occurredAt: new Date('2026-08-08T10:05:00Z'),
}];

describe('RelationshipWorkspace', () => {
  it('presents evaluation state, evidence history, and an honest Stop entry point', () => {
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} />);

    expect(screen.getByText('Evaluation · TRIAL_ACTIVE')).toBeVisible();
    expect(screen.getAllByText('TRIAL ACTIVE')).toHaveLength(2);
    expect(screen.getAllByText('1', { selector: 'dd' })).toHaveLength(2);
    expect(screen.getByRole('button', { name: 'No active work to stop' })).toBeDisabled();
  });

  it('distinguishes an active relationship as live', () => {
    render(<RelationshipWorkspace relationship={{ ...relationship, state: 'ACTIVE' }} timeline={timeline} />);

    expect(screen.getByText('Live · ACTIVE')).toBeVisible();
  });
});