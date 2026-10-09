import { render, screen } from '@testing-library/react';
import { EmploymentWorkspaceV1FromJSON } from '@/lib/api/generated/employment/src';
import { ConversationalEmploymentWorkspace } from './ConversationalEmploymentWorkspace';

jest.mock('@/components/conversation/OpenConversationCommand', () => ({
  OpenConversationCommand: ({ label }: { label: string }) => <button type="button">{label}</button>,
}));

const source = {
  owner: 'BP',
  contractVersion: '1.0.0-candidate.2',
  sourceVersion: 'workspace-7',
  state: 'CURRENT',
  observedAt: '2026-10-08T10:00:00Z',
};

const phase = (name: string) => ({
  phase: name,
  status: 'IN_PROGRESS',
  progress: {
    mandatoryTotal: 2,
    mandatoryCompleted: 1,
    optionalTotal: 0,
    optionalCompleted: 0,
    blockedCount: 0,
    deferredCount: 0,
  },
  completedItems: [],
  inProgressItems: [],
  pendingItems: [],
  blockers: [],
  assumptions: [],
  dependencies: [],
  milestones: [],
  calendarCommitments: [],
  evidenceState: 'CURRENT',
  sourceFreshness: '2026-10-08T10:00:00Z',
  limitations: [],
  availableCommands: [],
  sources: [source],
});

describe('ConversationalEmploymentWorkspace', () => {
  it('CEW-FIT-10 preserves existing relationship controls when the candidate is disabled', () => {
    render(<ConversationalEmploymentWorkspace employment={{ state: 'unavailable', reason: 'candidate-disabled' }} />);

    expect(screen.getByText(/candidate capability is disabled/)).toBeInTheDocument();
    expect(screen.getByText(/Existing relationship controls remain available/)).toBeInTheDocument();
  });

  it('CEW-FIT-12 renders all phases with a persistent Emergency Stop action', () => {
    const workspace = EmploymentWorkspaceV1FromJSON({
      schemaVersion: '1.0',
      protocolVersion: '1.0-candidate',
      relationshipId: 'relationship-1',
      workspaceVersion: 'workspace-7',
      agentType: 'neutral-professional',
      agentVersion: '1.0.0',
      manifestVersion: '1.0.0',
      readiness: {
        induction: 'IN_PROGRESS',
        plan: 'DRAFT',
        operations: 'READ_ONLY',
        performance: 'UNKNOWN',
        unmetConditions: ['plan acceptance required'],
        sources: [source],
      },
      phases: [phase('INDUCTION'), phase('PLANNING'), phase('OPERATIONS')],
      operations: {
        mode: 'READ_ONLY',
        eligibility: 'READ_ONLY',
        eligibleSkillRefs: [],
        lockedSkillRefs: ['skill-a'],
        permittedOperationClasses: ['READ_ONLY'],
        stopReachable: true,
        commercialSource: {
          ...source,
          owner: 'WBE',
          sourceVersion: 'commercial-3',
        },
      },
      sources: [source],
      limitations: ['Consequential work remains locked.'],
      recommendedNextAction: 'Complete planning review.',
      availableCommands: [
        {
          kind: 'SUBMIT_PLAN_FOR_REVIEW',
          subjectRef: 'plan-1',
          requiresExplicitAcknowledgement: false,
        },
      ],
      authoritativeCursor: 'cursor-7',
      producedAt: '2026-10-08T10:00:00Z',
    });

    render(<ConversationalEmploymentWorkspace employment={{ state: 'available', workspace }} />);

    expect(screen.getByText('induction')).toBeInTheDocument();
    expect(screen.getByText('planning')).toBeInTheDocument();
    expect(screen.getByText('operations')).toBeInTheDocument();
    expect(screen.getByText('Consequential work remains locked.')).toBeInTheDocument();
    expect(screen.getByText('Complete planning review.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();
    expect(screen.getByText(/Emergency Stop/)).toBeInTheDocument();
  });
});
