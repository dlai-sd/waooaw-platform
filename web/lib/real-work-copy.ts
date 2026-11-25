// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2 to DC-5 customer projections (WC170-R005 to WC170-R008)
// Constitutional basis: C-001, C-023, C-042, C-049, C-059, C-063

export type RealWorkCopy = {
  toolLabel: string;
  title: string;
  loading: string;
  unavailable: string;
  decisionsTitle: string;
  noDecisions: string;
  versionLabel: string;
  authorityLabel: string;
  limitationsLabel: string;
  seeEveryDetail: string;
  digestLabel: string;
  stepApprove: string;
  stepApproveQuestion: string;
  stepScope: string;
  stepScopeQuestion: string;
  approveAction: string;
  scopeAction: string;
  done: string;
  waiting: string;
  executable: string;
  replaced: string;
  strongSignIn: string;
  decisionFailed: string;
  timelineTitle: string;
  noTimeline: string;
  stopActive: string;
  details: string;
  evidenceCount: (count: number) => string;
  states: Record<string, string>;
  resultsTitle: string;
  activityTitle: string;
  activityNote: string;
  agentStatedTitle: string;
  businessResultsTitle: string;
  notMeasurable: string;
  noResults: string;
  withheld: (count: number) => string;
  traceLabel: string;
  workBehind: string;
  evidenceBehind: string;
  monitorOutcomeTitle: string;
  monitorPerformanceTitle: string;
  monitorTechnicalTitle: string;
  staleMarker: string;
};

// Hindi wording for this panel waits for the Founder's domain-wording confirmation, so every locale reads it in English.
export const realWorkCopy: RealWorkCopy = {
  toolLabel: 'Work',
  title: 'Work, decisions and results',
  loading: 'Loading the work…',
  unavailable: 'The work record is not available right now.',
  decisionsTitle: 'Your decisions',
  noDecisions: 'Nothing is waiting for you to decide.',
  versionLabel: 'Version',
  authorityLabel: 'What the agent may do',
  limitationsLabel: 'Limits you should know about',
  seeEveryDetail: 'See every detail you are approving',
  digestLabel: 'Exact version fingerprint',
  stepApprove: 'Step 1 · Approve',
  stepApproveQuestion: 'Do you approve this exact version?',
  stepScope: 'Step 2 · Confirm the boundary',
  stepScopeQuestion: 'Is it within what this agent may do for you, and who may do it?',
  approveAction: 'Approve this version',
  scopeAction: 'Confirm the boundary',
  done: 'Done',
  waiting: 'Waiting',
  executable: 'Both steps are done. The agent may work under this exact version.',
  replaced: 'Replaced by a newer version. It cannot be used for work.',
  strongSignIn: 'Sign in again with strong authentication to decide.',
  decisionFailed: 'The decision could not be recorded. Nothing was changed.',
  timelineTitle: 'What the agent is doing',
  noTimeline: 'The agent has not started any work yet.',
  stopActive: 'Emergency Stop is active. Work is halted and any later result is kept as evidence only.',
  details: 'Details',
  evidenceCount: (count) => `${count} evidence ${count === 1 ? 'item' : 'items'}`,
  states: {
    PROPOSED: 'Proposed',
    APPROVED: 'Approved',
    EXECUTING: 'Working',
    COMPLETED: 'Done',
    FAILED: 'Did not complete',
    HALTED: 'Halted',
  },
  resultsTitle: 'Results',
  activityTitle: 'Work completed',
  activityNote: 'This counts work done. It is activity, not a business result.',
  agentStatedTitle: 'Figures the agent reports',
  businessResultsTitle: 'Business results',
  notMeasurable: 'Not measurable yet',
  noResults: 'No completed work to show yet.',
  withheld: (count) =>
    `${count} reported ${count === 1 ? 'figure was' : 'figures were'} not shown because there is no work and evidence behind ${count === 1 ? 'it' : 'them'}.`,
  traceLabel: 'See what is behind this',
  workBehind: 'Work behind it',
  evidenceBehind: 'Evidence',
  monitorOutcomeTitle: 'Business results first',
  monitorPerformanceTitle: 'How your professional is doing',
  monitorTechnicalTitle: 'Technical details',
  staleMarker: 'Stale: not a current figure',
};
