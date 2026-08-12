import { fireEvent, render, screen, within } from '@testing-library/react';
import { RelationshipWorkspace } from './RelationshipWorkspace';
import type { ContractJourneyProjection, EmploymentRelationship, RelationshipEvaluationProjection, RelationshipTimelineEntry } from '@/lib/api/relationships';
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
  evidence: { schemaVersion: '1.0', relationshipId: relationship.relationshipId, items: [{ evidenceId: timeline[0].evidenceId, subject: 'TRIAL_STARTED', state: 'RECORDED' }] },
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
const contractJourney: ContractJourneyProjection = {
  contractId: 'ca57bbd1-62eb-48ab-bd78-2a23053f6551', version: 2, contractHash: 'exact-contract-hash',
  relationshipState: 'TRIAL_ACTIVE', acceptanceState: 'PENDING', paymentState: 'NOT_STARTED', activationState: 'NOT_STARTED',
  document: {
    professionalDisplayName: 'Digital Marketing Professional', rights: ['Inspect evidence', 'Choose not now'],
    obligations: ['Provide accurate context'], limitations: ['Cannot publish without authority'], authorityTerms: ['No publishing'], stopTerms: ['Emergency Stop remains available'],
    priceTax: { currency: 'INR', grossAmountInrPaise: 118000, gstAmountInrPaise: 18000, cadence: 'MONTHLY', subscriptionTerms: 'Monthly subscription', adSpendTreatment: 'Ad spend is separate', cancellationAndRefundTerms: 'Cancel before renewal; captured charges follow the stated refund policy' },
  },
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
    expect(screen.getByText('TRIAL_STARTED')).toBeVisible();
    expect(screen.getByText('Participant observation unresolved')).toBeVisible();
    expect(await screen.findByText('No messages yet. Start with a clear outcome for your professional.')).toBeVisible();
  });

  it('distinguishes an active relationship as live', async () => {
    render(<RelationshipWorkspace relationship={{ ...relationship, state: 'ACTIVE' }} timeline={timeline} views={views} evaluation={evaluation} />);

    expect(screen.getByText('Live · ACTIVE')).toBeVisible();
    expect(await screen.findByText('No messages yet. Start with a clear outcome for your professional.')).toBeVisible();
  });

  it('projects authoritative relationship Stop into the conversation controls', async () => {
    render(<RelationshipWorkspace relationship={{ ...relationship, state: 'STOPPED_EMERGENCY' }} timeline={timeline} views={views} evaluation={evaluation} />);

    expect(await screen.findByText('stopped', { exact: true })).toBeVisible();
    expect(screen.getByLabelText('Message your professional')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
    expect(screen.queryByText('live', { exact: true })).not.toBeInTheDocument();
  });

  it('CCT-AE01-DARK-01 shows exact terms and symmetric unselected contract decisions', async () => {
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} views={views} evaluation={evaluation} contractJourney={contractJourney} />);

    expect(screen.getByText('exact-contract-hash')).toBeVisible();
    expect(screen.getByText('₹1,180.00')).toBeVisible();
    expect(screen.getByText('₹180.00')).toBeVisible();
    expect(screen.getByText(/Ad spend is separate/)).toBeVisible();
    const decisions = screen.getByRole('group', { name: 'Contract decisions' });
    for (const name of ['Hire and accept exact contract', 'Not now', 'Cancel', 'Exit']) {
      expect(within(decisions).getByRole(name === 'Exit' ? 'link' : 'button', { name })).toBeVisible();
    }
    expect(within(decisions).queryByRole('button', { name: 'Proceed to Razorpay' })).not.toBeInTheDocument();
    expect(within(decisions).queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByText(/hurry|expires in|last chance/i)).not.toBeInTheDocument();
    fireEvent.click(within(decisions).getByRole('button', { name: 'Hire and accept exact contract' }));
    const proceed = await within(decisions).findByRole('button', { name: 'Proceed to Razorpay' });
    expect(proceed).toBeVisible();
    expect(screen.getByText('Contract accepted and evidenced. Payment has not started.')).toBeVisible();
    fireEvent.click(proceed);
    expect(await screen.findByText(/Payment remains unconfirmed until hosted checkout capture/)).toBeVisible();
    fireEvent.click(within(decisions).getByRole('button', { name: 'Not now' }));
    expect(screen.getByText('Not now selected. No contract or payment state changed.')).toBeVisible();
    fireEvent.click(within(decisions).getByRole('button', { name: 'Cancel' }));
    expect(screen.getByText('Cancelled. No contract or payment state changed.')).toBeVisible();
  });

  it('keeps failed payment explicitly unresolved', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ title: 'Payment owner is unavailable.' }),
    } as Response);
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} views={views} evaluation={evaluation} contractJourney={{ ...contractJourney, acceptanceState: 'ACCEPTED' }} />);
    const contractSection = screen.getByRole('heading', { name: 'Employment contract' }).closest('section')!;

    fireEvent.click(screen.getByRole('button', { name: 'Proceed to Razorpay' }));

    expect(await within(contractSection).findByText('Payment owner is unavailable.')).toBeVisible();
    expect(screen.queryByText(/payment succeeded/i)).not.toBeInTheDocument();
  });
});