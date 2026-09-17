import { fireEvent, render, screen, within } from '@testing-library/react';
import { RelationshipWorkspace } from './RelationshipWorkspace';
import type { ContractJourneyProjection, EmploymentRelationship, RelationshipEvaluationProjection, RelationshipTimelineEntry } from '@/lib/api/relationships';
import type { RelationshipWorkspaceViews } from '@/lib/api/relationship-workspace';
import type { AgentEmploymentLifecycleStageV1, PerformanceReviewWindowV1 } from '@/lib/api/generated';

const relationship: EmploymentRelationship = {
  relationshipId: '5f33925b-fb0c-4366-8414-7f85309639b9',
  agentInstanceId: '19382d51-0124-43c1-a732-777fe0b00d63',
  professionalType: 'DIGITAL_MARKETING',
  agentInstanceMintedAt: new Date('2026-08-08T10:00:00Z'),
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
const lifecycleStages = (['ONBOARD', 'INDUCT', 'GOAL_VERIFICATION', 'BUSINESS_OUTCOMES', 'OPERATIONS'] as const)
  .map((stage): AgentEmploymentLifecycleStageV1 => ({
    stage,
    state: stage === 'ONBOARD' || stage === 'INDUCT' ? 'VERIFIED' : 'NOT_STARTED',
    owner: 'BP',
    inputRevisions: ['relationship-1'],
    evidenceState: 'RECORDED',
    freshness: 'CURRENT',
    completionCriteria: `${stage} completion criteria`,
    blockerReasons: [],
    nextAuthorizedAction: `continue-${stage.toLowerCase()}`,
  }));
const views: RelationshipWorkspaceViews = {
  workspace: {
    schemaVersion: '1.0', relationshipId: relationship.relationshipId, workspaceVersion: 'relationship-1',
    snapshotState: 'PARTIAL', currencyState: 'CURRENT', authoritativeCursor: 'workspace:relationship:00000001',
    producedAt: new Date('2026-08-10T10:00:00Z'),
    context: {
      relationshipId: relationship.relationshipId,
      agentInstanceId: relationship.agentInstanceId,
      professionalType: relationship.professionalType,
      lifecycleState: 'TRIAL_ACTIVE',
      policySelection: { f4Pol01: 'A', f4Pol02: 'A', f4Pol03: 'B', f4Pol04: 'A', f4Pol05: 'B', f4Pol06: 'A' },
    },
    lifecycleProfile: {
      agentInstanceId: relationship.agentInstanceId,
      relationshipVersion: relationship.stateVersion,
      producedAt: new Date('2026-08-10T10:00:00Z'),
      stages: lifecycleStages,
    },
    sections: [],
  },
  configuration: {
    ...section, sectionType: 'CONFIGURATION', lifecyclePhase: 'GOAL_VERIFICATION',
    items: [
      { stepKey: 'ONBOARD', label: 'Onboard', state: 'VERIFIED', summary: 'Preferences confirmed' },
      { stepKey: 'INDUCT', label: 'Induct', state: 'VERIFIED', summary: 'Context confirmed' },
    ],
  },
  goals: {
    ...section, sectionType: 'GOALS', activeGoals: [{
      goalId: 'goal-1', goalVersion: '1', skillId: 'MARKET_RESEARCH', skillLabel: 'Market research',
      measure: 'Qualified enquiries', frequency: 'MONTHLY', verificationStatus: 'PENDING_CUSTOMER', status: 'ACTIVE',
    }], history: [],
  },
  businessOutcomes: { ...section, sectionType: 'BUSINESS_OUTCOMES', items: [] },
  performance: { ...section, sectionType: 'PERFORMANCE', current: null, history: [] },
  operations: {
    ...section, sectionType: 'OPERATIONS', eligibilityState: 'LOCKED', requiredGoalIds: ['goal-1'],
    verifiedGoalIds: [], blockedReasons: ['Customer goal verification is required.'],
    reassessmentRequired: false, dependentOutcomeIds: [], operationalMandate: null,
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
  skills: [{ configurationId: 'skill-1', skillId: 'MARKET_RESEARCH', skillVersion: '1.0.0', subjectVersion: 'skill-4', applicability: 'APPLICABLE', authorityState: 'NOT_GRANTED', status: 'DEFERRED' }],
  decisionSpace: { version: 1, budgetCeilingInrPaise: 100000, authorityBoundaries: ['No publishing'], stopConditions: ['Customer stop'], reviewCadenceMonths: 2 },
};
const contractJourney: ContractJourneyProjection = {
  contractId: 'ca57bbd1-62eb-48ab-bd78-2a23053f6551', version: 2, contractHash: 'exact-contract-hash',
  relationshipState: 'TRIAL_ACTIVE', acceptanceState: 'PENDING', paymentState: 'NOT_STARTED', activationState: 'NOT_STARTED',
  document: {
    professionalDisplayName: 'Digital Marketing Professional', rights: ['Inspect evidence', 'Choose not now'],
    obligations: ['Provide accurate context'], limitations: ['Cannot publish without authority'], authorityTerms: ['No publishing'], stopTerms: ['Emergency Stop remains available'],
    priceTax: { currency: 'INR', grossAmountInrPaise: 118000, gstAmountInrPaise: 18000, cadence: 'MONTHLY', subscriptionTerms: 'Monthly subscription', adSpendTreatment: 'Ad spend is separate', cancellationAndRefundTerms: 'Cancel before renewal; captured charges follow the stated refund policy', offeringId: 'dma-release-1', bundleTier: 'STARTER', quoteVersion: 'quote-v1', renewalConsequence: 'Renews at the accepted monthly price' },
  },
};
const performanceReview: PerformanceReviewWindowV1 = {
  reviewId: '725792fa-c9c1-4377-b3db-0fb41b091279',
  agentInstanceId: relationship.agentInstanceId,
  skillId: 'MARKET_RESEARCH',
  skillVersion: '1.0.0',
  revision: 1,
  policyVersion: 'review-policy-1',
  periodStart: new Date('2026-08-01T00:00:00Z'),
  periodEnd: new Date('2026-08-31T00:00:00Z'),
  sourceVersions: { professionalRuntime: 'pr-17', constitutionalEngine: 'ce-9' },
  workDelivery: { state: 'DELIVERED', summary: 'Work delivered.', evidenceState: 'RECORDED' },
  agentQuality: { state: 'GOOD', summary: 'Quality passed.', evidenceState: 'RECORDED' },
  constitutionalPerformance: { state: 'CONFORMANT', summary: 'Evidence complete.', evidenceState: 'RECORDED' },
  commercialUsage: { state: 'WITHIN_ALLOWANCE', summary: 'Within allowance.', evidenceState: 'RECORDED' },
  customerBusinessOutcome: { state: 'POOR', summary: 'Outcome did not improve.', evidenceState: 'RECORDED', attributionLimits: 'No causal guarantee' },
  customerAssessment: { state: 'CUSTOMER_DISPUTED', summary: 'Customer requested correction.', evidenceState: 'RECORDED' },
  trustAutonomy: { state: 'UNCHANGED', summary: 'No autonomy increase.', evidenceState: 'RECORDED' },
  recommendation: 'REASSESSMENT_REQUIRED' as const,
  evidenceId: '5bbc4e01-461a-4c51-99d8-59bb5daa85f1',
  createdAt: new Date('2026-09-01T00:00:00Z'),
  customerResponse: null,
  reassessmentRequired: true,
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

  it('SIM-095-14 separates good agent quality from poor business outcome and unchanged trust', () => {
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} evaluation={evaluation} views={{
      ...views,
      performance: {
        ...views.performance,
        currencyState: 'CURRENT',
        current: performanceReview,
      },
    }} />);

    expect(screen.getByText('good')).toBeVisible();
    expect(screen.getByText('poor')).toBeVisible();
    expect(screen.getByText('unchanged')).toBeVisible();
    expect(screen.getByText(/reassessment required/)).toBeVisible();
    expect(screen.getByText('No causal guarantee')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Record review decision' })).toBeVisible();
  });

  it('submits an exact-version customer review decision for only the current relationship', async () => {
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} evaluation={evaluation} views={{
      ...views,
      performance: { ...views.performance, currencyState: 'CURRENT', current: performanceReview },
    }} />);

    fireEvent.change(screen.getByLabelText('Decision'), { target: { value: 'REQUEST_REASSESSMENT' } });
    fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Outcome requires a revised plan.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record review decision' }));

    expect(await screen.findByText(/Review decision recorded/)).toBeVisible();
    const reviewCall = (global.fetch as jest.Mock).mock.calls.find(([url]) => String(url).endsWith('/performance-reviews'));
    expect(reviewCall?.[0]).toBe(`/api/relationships/${relationship.relationshipId}/performance-reviews`);
    expect(JSON.parse(reviewCall?.[1].body)).toMatchObject({
      command: {
        expectedWorkspaceVersion: 'relationship-1',
        expectedSubjectVersion: `performance-${performanceReview.reviewId}-1`,
        payload: {
          commandKind: 'RESPOND_TO_PERFORMANCE_REVIEW', reviewId: performanceReview.reviewId,
          reviewRevision: 1, decision: 'REQUEST_REASSESSMENT', reason: 'Outcome requires a revised plan.',
        },
      },
    });
  });

  afterEach(() => jest.restoreAllMocks());

  it('presents evaluation state and evidence history', async () => {
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} views={views} evaluation={evaluation} />);

    expect(screen.getByRole('complementary', { name: 'Your agents' })).toBeVisible();
    const contextNavigation = screen.getByRole('navigation', { name: 'Relationship context' });
    expect(contextNavigation).toBeVisible();
    expect(within(contextNavigation).getByRole('link', { name: 'Usage & budget' })).toHaveAttribute('href', '#usage-and-budget');
    expect(within(contextNavigation).getByRole('link', { name: 'Rights & control' })).toHaveAttribute('href', '#rights-and-control');
    expect(screen.getByRole('link', { name: relationship.professionalType })).toHaveAttribute('aria-current', 'page');
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
  });

  it('distinguishes an active relationship as live', async () => {
    render(<RelationshipWorkspace relationship={{ ...relationship, state: 'ACTIVE' }} timeline={timeline} views={views} evaluation={evaluation} />);

    expect(screen.getByText('Live · ACTIVE')).toBeVisible();
  });

  it('switches experts by relationship without mutating either relationship', () => {
    const otherRelationshipId = 'b9baf6eb-0800-4482-8879-e23c124ed410';
    render(<RelationshipWorkspace relationship={relationship} relationships={[
      {
        relationshipId: relationship.relationshipId, agentInstanceId: relationship.agentInstanceId,
        professionalType: relationship.professionalType, professionalDisplayName: 'Digital marketing expert',
        lifecycleState: 'TRIAL_ACTIVE', unreadState: 'NONE', availabilityState: 'AVAILABLE', currencyState: 'CURRENT',
        configurationState: 'IN_PROGRESS', enabledSkillCount: 1, pendingSkillCount: 0,
        performanceSummary: 'No evidenced performance summary is available yet.',
        billingSummary: 'No current billing amount is available in this summary.', nextActionLabel: 'Open conversation',
        lastAuthoritativelyConfirmedAt: relationship.updatedAt,
        resumeTarget: { surface: 'CONVERSATION', relationshipId: relationship.relationshipId },
      },
      {
        relationshipId: otherRelationshipId, agentInstanceId: 'a1a81eb7-6258-45d4-8cc1-c947e029042c',
        professionalType: 'DIGITAL_MARKETING', professionalDisplayName: 'Campaign expert',
        lifecycleState: 'ACTIVE', unreadState: 'ACTION_REQUIRED', availabilityState: 'AVAILABLE', currencyState: 'CURRENT',
        configurationState: 'COMPLETE', enabledSkillCount: 2, pendingSkillCount: 0,
        performanceSummary: 'No evidenced performance summary is available yet.',
        billingSummary: 'No current billing amount is available in this summary.', nextActionLabel: 'View work',
        lastAuthoritativelyConfirmedAt: relationship.updatedAt,
        resumeTarget: { surface: 'CONVERSATION', relationshipId: otherRelationshipId },
      },
    ]} timeline={timeline} views={views} evaluation={evaluation} />);

    const switcher = screen.getByRole('navigation', { name: 'Switch expert' });
    expect(within(switcher).getByRole('link', { name: 'Digital marketing expert' })).toHaveAttribute('aria-current', 'page');
    expect(within(switcher).getByRole('link', { name: 'Campaign expert' })).toHaveAttribute('href', `/relationships/${otherRelationshipId}`);
  });

  it('submits an exact-version skill decision for only the current relationship', async () => {
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} views={views} evaluation={evaluation} />);

    fireEvent.click(screen.getByRole('button', { name: 'accept' }));

    expect(await screen.findByText('Skill decision recorded.')).toBeVisible();
    const skillCall = (global.fetch as jest.Mock).mock.calls.find(([url]) => String(url).endsWith('/skill-decisions'));
    expect(skillCall?.[0]).toBe(`/api/relationships/${relationship.relationshipId}/skill-decisions`);
    expect(JSON.parse(skillCall?.[1].body)).toMatchObject({
      command: {
        expectedWorkspaceVersion: 'relationship-1', expectedSubjectVersion: 'skill-4',
        payload: { commandKind: 'ACCEPT_SKILL', configurationId: 'skill-1', skillId: 'MARKET_RESEARCH', skillVersion: '1.0.0' },
      },
    });
  });

  it('submits exact-version customer goal verification for only the current relationship', async () => {
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} views={views} evaluation={evaluation} />);

    fireEvent.click(screen.getByRole('button', { name: 'Verify goal' }));

    expect(await screen.findByText('Goal verification recorded.')).toBeVisible();
    const goalCall = (global.fetch as jest.Mock).mock.calls.find(([url]) => String(url).endsWith('/goal-verifications'));
    expect(goalCall?.[0]).toBe(`/api/relationships/${relationship.relationshipId}/goal-verifications`);
    expect(JSON.parse(goalCall?.[1].body)).toMatchObject({
      command: {
        schemaVersion: '1.0', expectedWorkspaceVersion: 'relationship-1', expectedSubjectVersion: '1',
        payload: { commandKind: 'VERIFY_GOAL', goalId: 'goal-1', goalVersion: '1', verificationDecision: 'VERIFIED' },
      },
    });
    expect(JSON.parse(String(goalCall?.[1]?.body)).command.payload).not.toHaveProperty('correctionReason');
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
    expect(within(decisions).queryByRole('button', { name: 'Continue to payment' })).not.toBeInTheDocument();
    expect(within(decisions).queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByText(/hurry|expires in|last chance/i)).not.toBeInTheDocument();
    fireEvent.click(within(decisions).getByRole('button', { name: 'Hire and accept exact contract' }));
    const proceed = await within(decisions).findByRole('button', { name: 'Continue to payment' });
    expect(proceed).toBeVisible();
    expect(screen.getByText('Contract accepted and evidenced. Payment has not started.')).toBeVisible();
    fireEvent.click(proceed);
    expect(await screen.findByText(/Checkout remains unresolved/)).toBeVisible();
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

    fireEvent.click(screen.getByRole('button', { name: 'Continue to payment' }));

    expect(await within(contractSection).findByText('Payment owner is unavailable.')).toBeVisible();
    expect(screen.queryByText(/payment succeeded/i)).not.toBeInTheDocument();
  });

  it('launches official Razorpay Checkout and treats its callback only as a reconciliation prompt', async () => {
    let checkoutOptions: Record<string, unknown> | undefined;
    const open = jest.fn(() => (checkoutOptions?.handler as (() => void))());
    Object.defineProperty(window, 'Razorpay', {
      configurable: true,
      value: function Razorpay(options: Record<string, unknown>) {
        checkoutOptions = options;
        return { open };
      },
    });
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          outcomeKind: 'RAZORPAY_CHECKOUT_REQUIRED',
          checkoutIntentId: '7bc5b28a-a674-4c77-b3e0-7da0f8bf1e50',
          providerOrderReference: 'order_exact',
          publicCheckoutKey: 'rzp_test_public',
          amountInrPaise: 118000,
          currency: 'INR',
          merchantDisplayName: 'WAOOAW',
          enabledMethodFamilies: ['CREDIT_CARD', 'DEBIT_CARD', 'UPI', 'NETBANKING', 'WALLET'],
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          outcomeKind: 'CAPTURED',
          checkoutIntentId: '7bc5b28a-a674-4c77-b3e0-7da0f8bf1e50',
          commercialOutcomeReference: 'pay_exact',
          commercialEvidenceId: '14eddf57-ef75-4a94-bfac-06b2b550dd44',
        }),
      } as Response);
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} views={views} evaluation={evaluation} contractJourney={{ ...contractJourney, acceptanceState: 'ACCEPTED' }} />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue to payment' }));

    expect(await screen.findByRole('button', { name: 'Complete paid activation' })).toBeVisible();
    expect(open).toHaveBeenCalledTimes(1);
    expect(checkoutOptions).toEqual(expect.objectContaining({
      key: 'rzp_test_public', amount: 118000, currency: 'INR', order_id: 'order_exact',
    }));
    const reconciliationCall = (global.fetch as jest.Mock).mock.calls[1];
    expect(reconciliationCall[0]).toContain('checkoutIntentId=7bc5b28a-a674-4c77-b3e0-7da0f8bf1e50');
    expect(reconciliationCall[1]).not.toHaveProperty('body');
    expect(screen.getByText(/signature-verified and reconciled/)).toBeVisible();
  });

  it('keeps Razorpay Checkout dismissal non-terminal without callback or activation', async () => {
    let checkoutOptions: Record<string, unknown> | undefined;
    Object.defineProperty(window, 'Razorpay', {
      configurable: true,
      value: function Razorpay(options: Record<string, unknown>) {
        checkoutOptions = options;
        return { open: () => ((options.modal as { ondismiss(): void }).ondismiss()) };
      },
    });
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcomeKind: 'RAZORPAY_CHECKOUT_REQUIRED',
        checkoutIntentId: '7bc5b28a-a674-4c77-b3e0-7da0f8bf1e50',
        providerOrderReference: 'order_exact',
        publicCheckoutKey: 'rzp_test_public',
        amountInrPaise: 118000,
        currency: 'INR',
        merchantDisplayName: 'WAOOAW',
      }),
    } as Response);
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} views={views} evaluation={evaluation} contractJourney={{ ...contractJourney, acceptanceState: 'ACCEPTED' }} />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue to payment' }));

    expect(await screen.findByText(/closed. Payment is not marked failed/)).toBeVisible();
    expect(checkoutOptions).toBeDefined();
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('button', { name: 'Complete paid activation' })).not.toBeInTheDocument();
    expect(screen.queryByText(/payment failed/i)).not.toBeInTheDocument();
  });

  it('renders a truthful non-collecting Demo zero-price checkout', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcomeKind: 'FULLY_DISCOUNTED',
        payableInrPaise: 0,
        listPriceInrPaise: 118000,
        discountInrPaise: 118000,
        taxInrPaise: 18000,
        renewalConsequence: 'Renews at the accepted monthly price',
        commercialOutcomeReference: 'zero-price:intent-1',
        commercialEvidenceId: '14eddf57-ef75-4a94-bfac-06b2b550dd44',
      }),
    } as Response);
    render(<RelationshipWorkspace relationship={relationship} timeline={timeline} views={views} evaluation={evaluation} contractJourney={{ ...contractJourney, acceptanceState: 'ACCEPTED' }} />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue to payment' }));

    expect(await screen.findByText('100% Demo discount applied. Amount paid: INR 0. No payment method charged.')).toBeVisible();
    expect(screen.getByText('Amount paid').nextSibling).toHaveTextContent('INR 0');
    for (const method of ['Credit card', 'Debit card', 'UPI', 'Netbanking', 'Wallet']) {
      expect(screen.getByText(method)).toBeVisible();
    }
    expect(screen.getAllByText('Not required - 100% Demo discount applied')).toHaveLength(5);
    expect(screen.getByText('No bank, card network, UPI app, wallet, or Razorpay processed money.')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: 'Complete fully discounted activation' }));

    expect(await screen.findByText('Employment relationship activated. Amount paid: INR 0.')).toBeVisible();
    const activationCall = (global.fetch as jest.Mock).mock.calls.find(([, options]) =>
      typeof options?.body === 'string' && JSON.parse(options.body).action === 'activate');
    expect(JSON.parse(String(activationCall?.[1]?.body))).toMatchObject({
      commercialOutcomeKind: 'ZERO_PRICE_SATISFIED',
      commercialOutcomeReference: 'zero-price:intent-1',
      commercialEvidenceId: '14eddf57-ef75-4a94-bfac-06b2b550dd44',
    });
  });
});