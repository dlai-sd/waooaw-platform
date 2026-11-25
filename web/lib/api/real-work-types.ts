// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2 to DC-5 customer projections (WC170-R005 to WC170-R008)
// Constitutional basis: C-001, C-023, C-049, C-059, C-063

export type ArtifactStatus = 'DRAFT' | 'PROPOSED' | 'LOCKED' | 'SUPERSEDED';

export type RealWorkArtifact = {
  artifactId: string;
  artifactType: string;
  version: number;
  digest: string;
  status: ArtifactStatus;
  lockedAt?: string | null;
  approvalEvidenceId?: string | null;
  supersedesArtifactId?: string | null;
  plainLanguageSummary: string;
  limitations: string[];
  authorityBoundary?: string | null;
  vocabularyVersion?: string | null;
  vocabularyDigest?: string | null;
  content?: unknown;
};

export type DecisionView = {
  kind: 'APPROVAL' | 'SCOPE_CONFIRMATION';
  evidenceId: string;
  decidedAt: string;
  decisionSpaceVersion?: number | null;
};

export type ArtifactDecisionState = {
  approval: DecisionView | null;
  scopeConfirmation: DecisionView | null;
  executable: boolean;
  blockedReason: string | null;
};

export type RealWorkArtifactItem = { artifact: RealWorkArtifact; decisions: ArtifactDecisionState };

export type CommandContext = { workspaceVersion: string; manifestVersion: string; decisionSpaceVersion: number };

export type RealWorkArtifacts = { commandContext: CommandContext | null; items: RealWorkArtifactItem[] };

export type TimelineState = 'PROPOSED' | 'APPROVED' | 'EXECUTING' | 'COMPLETED' | 'FAILED' | 'HALTED';

export type TimelineEvent = {
  eventId: string;
  workItemId: string;
  workItemType: string;
  state: TimelineState;
  artifactId?: string | null;
  artifactDigest?: string | null;
  evidenceRefs: string[];
  reasonCode?: string | null;
  providerReference?: string | null;
  occurredAt: string;
  sequence: number;
  sentence: string;
};

export type TimelineWorkItem = {
  workItemId: string;
  workItemType: string;
  state: TimelineState;
  reasonCode?: string | null;
  sentence: string;
  events: TimelineEvent[];
};

export type RealWorkTimeline = {
  relationshipId: string;
  events: TimelineEvent[];
  workItems: TimelineWorkItem[];
  emergencyStopActive: boolean;
};

export type OutcomeClaim = {
  claimId: string;
  measureId: string;
  claimText: string;
  category: 'ACTIVITY' | 'OUTCOME';
  derivation: 'INDEPENDENT' | 'AGENT_STATED';
  label?: string | null;
  value?: number | null;
  unit: string;
  asOf: string;
  workItemIds: string[];
  evidenceIds: string[];
  limitations: string[];
};

export type RealWorkOutcomes = {
  relationshipId: string;
  activity: OutcomeClaim[];
  outcomes: OutcomeClaim[];
  agentStated: OutcomeClaim[];
  notMeasurableYet: Array<{ measureId: string; text: string }>;
  withheldClaims: number;
};

export type OutcomeTrace = { claim: OutcomeClaim; workItems: TimelineWorkItem[]; evidence: string[] };

export type RealWorkSnapshot = {
  artifacts: RealWorkArtifacts | null;
  timeline: RealWorkTimeline | null;
  outcomes: RealWorkOutcomes | null;
};

export type DecisionCommandKind = 'ACCEPT_ARTIFACT_VERSION' | 'CONFIRM_SCOPE_BOUNDARY';

const labelOf = (value: string) => value.replaceAll('_', ' ').toLowerCase();
export const humanize = (value: string) => {
  const text = labelOf(value);
  return text.charAt(0).toUpperCase() + text.slice(1);
};
