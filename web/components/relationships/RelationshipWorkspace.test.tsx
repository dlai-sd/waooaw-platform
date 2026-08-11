import { render, screen, within } from '@testing-library/react';
import { RelationshipWorkspace } from './RelationshipWorkspace';
import type { EmploymentRelationship, RelationshipEvaluationProjection, RelationshipTimelineEntry } from '@/lib/api/relationships';
import type { RelationshipWorkspaceViews } from '@/lib/api/relationship-workspace';

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

const provenance = { owner: 'BP', sourceProjectionVersion: 'relationship-1', producedAt: new Date('2026-08-10T10:00:00Z') };
const section = { currencyState: 'UNAVAILABLE' as const, provenance, availableCommands: [] };
const views: RelationshipWorkspaceViews = {
  workspace: {
    schemaVersion: '1.0', relationshipId: relationship.relationshipId, workspaceVersion: 'relationship-1',
    snapshotState: 'PARTIAL', currencyState: 'CURRENT', authoritativeCursor: 'workspace:relationship:00000001',
    producedAt: new Date('2026-08-10T10:00:00Z'),
    context: { relationshipId: relationship.relationshipId, lifecycleState: 'TRIAL_ACTIVE', policySelection: { f4Pol01: 'A', f4Pol02: 'A', f4Pol03: 'B', f4Pol04: 'A', f4Pol05: 'B', f4Pol06: 'A' } },
    sections: [],
  },
  plan: { ...section, sectionType: 'PLAN', planId: relationship.relationshipId, goals: [] },
  attention: { ...section, sectionType: 'ATTENTION', currencyState: 'CURRENT', items: [] },
  work: { ...section, sectionType: 'WORK', items: [] },
  results: { ...section, sectionType: 'RESULTS', outcomes: [] },
  usageBudget: { ...section, sectionType: 'USAGE_BUDGET', actualAmount: 'Unavailable', forecastRange: 'Unavailable' },
  rightsControls: { ...section, sectionType: 'RIGHTS_CONTROLS', currencyState: 'CURRENT', scopeVersion: '1', authorityVersion: '1', lifecycleState: 'TRIAL_ACTIVE', emergencyStopReachable: true },
};
const evaluation: RelationshipEvaluationProjection = {
  relationshipId: relationship.relationshipId,
  lifecycleState: 'TRIAL_ACTIVE',
  interviewState: 'AVAILABLE',
  context: [{ payloadReference: 'context-1', fieldType: 'NAME', value: 'Acme Clinic', status: 'CONFIRMED' }],
  nextContextQuestion: 'Where does your business serve customers?',
  trial: { trialId: 'trial-1', startsAt: '2026-08-08T10:00:00Z', expiresAt: '2026-08-22T10:00:00Z', status: 'ACTIVE' },
  goals: [{ goalId: 'goal-1', goal: 'Increase enquiries', measure: 'Qualified enquiries', status: 'ACCEPTED', reviewCadenceMonths: 2 }],
  skills: [{ configurationId: 'skill-1', skillId: 'MARKET_RESEARCH', applicability: 'APPLICABLE', authorityState: 'NOT_GRANTED', status: 'DEFERRED' }],
  decisionSpace: { version: 1, budgetCeilingInrPaise: 100000, authorityBoundaries: ['No publishing'], stopConditions: ['Customer stop'], reviewCadenceMonths: 2 },
};

describe('RelationshipWorkspace', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        schemaVersion: '1.0',
        relationshipId: relationship.relationshipId,
        items: [],
        authoritativeCursor: 'authoritative-cursor',
        hasMore: false,
        serverTime: '2026-08-10T10:01:00Z',
      }),
    } as Response);
  });

  afterEach(() => jest.restoreAllMocks());

  it('presents evaluation state and evidence history', async () => {
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} views={views} evaluation={evaluation} />);

    expect(screen.getByText('Evaluation · TRIAL_ACTIVE')).toBeVisible();
    expect(screen.getAllByText('TRIAL ACTIVE')).toHaveLength(2);
    expect(within(screen.getByText('Version').parentElement!).getByText('1')).toBeVisible();
    expect(screen.getByText('Nothing currently requires your response.')).toBeVisible();
    expect(screen.getByText('No supported business outcome is available yet.')).toBeVisible();
    expect(screen.getByText('Where does your business serve customers?')).toBeVisible();
    expect(screen.getByText(/Trial quota is unavailable/)).toBeVisible();
    expect(screen.getByText('deferred')).toBeVisible();
    expect(await screen.findByText('No messages yet. Start with a clear outcome for your professional.')).toBeVisible();
  });

  it('distinguishes an active relationship as live', async () => {
    render(<RelationshipWorkspace relationship={{ ...relationship, state: 'ACTIVE' }} timeline={timeline} views={views} evaluation={evaluation} />);

    expect(screen.getByText('Live · ACTIVE')).toBeVisible();
    expect(await screen.findByText('No messages yet. Start with a clear outcome for your professional.')).toBeVisible();
  });
});