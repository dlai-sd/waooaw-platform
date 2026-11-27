// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R024
// Constitutional basis: C-023, C-059, C-063

export type ApprovalState = 'NOT_APPROVED' | 'APPROVED' | 'SUSPENDED' | 'RETIRED';
export type ApprovalAction = 'approve' | 'suspend' | 'retire';

export type ProfessionalApproval = {
  professionalType: string;
  professionalVersion: string;
  displayName: string;
  state: ApprovalState;
  definitionChanged: boolean;
  decidedBy: string | null;
  decidedAt: string | null;
  reason: string | null;
  stateVersion: number;
  actions: ApprovalAction[];
};

const states: readonly string[] = ['NOT_APPROVED', 'APPROVED', 'SUSPENDED', 'RETIRED'];
const actions: readonly string[] = ['approve', 'suspend', 'retire'];

export function asApproval(value: unknown): ProfessionalApproval | null {
  const candidate = value as Partial<ProfessionalApproval> | null;
  if (
    !candidate ||
    typeof candidate.professionalType !== 'string' ||
    typeof candidate.professionalVersion !== 'string' ||
    typeof candidate.displayName !== 'string' ||
    typeof candidate.state !== 'string' ||
    !states.includes(candidate.state) ||
    typeof candidate.definitionChanged !== 'boolean' ||
    typeof candidate.stateVersion !== 'number' ||
    !Array.isArray(candidate.actions) ||
    candidate.actions.some((action) => typeof action !== 'string' || !actions.includes(action))
  )
    return null;
  return {
    ...(candidate as ProfessionalApproval),
    decidedBy: typeof candidate.decidedBy === 'string' ? candidate.decidedBy : null,
    decidedAt: typeof candidate.decidedAt === 'string' ? candidate.decidedAt : null,
    reason: typeof candidate.reason === 'string' ? candidate.reason : null,
  };
}

export function asApprovals(value: unknown): ProfessionalApproval[] | null {
  const items = (value as { items?: unknown } | null)?.items;
  if (!Array.isArray(items)) return null;
  const parsed = items.map(asApproval);
  return parsed.every((item): item is ProfessionalApproval => item !== null) ? parsed : null;
}

export const stateWords: Record<ApprovalState, string> = {
  NOT_APPROVED: 'Not approved yet',
  APPROVED: 'Approved for customers',
  SUSPENDED: 'Suspended',
  RETIRED: 'Retired',
};

export const stateExplanation: Record<ApprovalState, string> = {
  NOT_APPROVED: 'Customers cannot start a Trial or Hire with this professional until you approve it.',
  APPROVED: 'Customers can start a Trial or Hire. New customers are stopped the moment you suspend or retire it.',
  SUSPENDED: 'No new Trial or Hire can start. You can approve it again at any time.',
  RETIRED: 'No new Trial or Hire can start, and this version cannot be approved again. Publish a new version instead.',
};

export const actionWords: Record<ApprovalAction, string> = {
  approve: 'Approve for customers',
  suspend: 'Suspend',
  retire: 'Retire',
};

const failureWords: Record<string, string> = {
  PROFESSIONAL_APPROVAL_FORBIDDEN: 'Only the Founder can decide this.',
  PROFESSIONAL_APPROVAL_REASON_REQUIRED: 'Give a short reason (at least 5 characters).',
  PROFESSIONAL_APPROVAL_REASON_TOO_LONG: 'The reason can be at most 500 characters.',
  PROFESSIONAL_APPROVAL_RETIRED: 'A retired version cannot be approved again. Publish a new version instead.',
  PROFESSIONAL_APPROVAL_NOT_ALLOWED: 'That decision is not available for this version right now.',
  PROFESSIONAL_APPROVAL_CONFLICT: 'Another decision was saved first. Reload and try again.',
  PROFESSIONAL_APPROVAL_UNKNOWN: 'That professional version is not in this release.',
};

export function failureMessage(code: unknown): string {
  return (
    (typeof code === 'string' && failureWords[code]) ||
    'The decision could not be saved. Nothing was changed. Try again.'
  );
}
