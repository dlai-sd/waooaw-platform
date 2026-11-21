// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-059, C-063, ADR-051

import { render, screen } from '@testing-library/react';
import RelationshipPage from '@/app/(application)/relationships/[relationshipId]/page';
import { getEmploymentWorkspace } from '@/lib/api/employment-workspace';
import { getCustomerEngagementProgress } from '@/lib/api/customer-engagement';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { getRelationshipWorkspaceViews } from '@/lib/api/relationship-workspace';
import {
  getContractJourney,
  getRelationship,
  getRelationshipEvaluation,
  getRelationshipTimeline,
  listEmploymentRelationships,
} from '@/lib/api/relationships';
import { getWorkbench } from '@/lib/api/workbench';
import { getRequestI18n } from '@/lib/i18n-server';
import { getServerAccessToken } from '@/lib/server-auth';

jest.mock('next/navigation', () => ({
  redirect: (target: string) => {
    throw new Error(`redirect:${target}`);
  },
}));
jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({ getRequestI18n: jest.fn() }));
jest.mock('@/lib/api/workbench', () => ({ getWorkbench: jest.fn() }));
jest.mock('@/lib/api/relationships', () => ({
  getRelationship: jest.fn(),
  getRelationshipTimeline: jest.fn(),
  getRelationshipEvaluation: jest.fn(),
  getContractJourney: jest.fn(),
  listEmploymentRelationships: jest.fn(),
}));
jest.mock('@/lib/api/relationship-workspace', () => ({ getRelationshipWorkspaceViews: jest.fn() }));
jest.mock('@/lib/api/employment-workspace', () => ({ getEmploymentWorkspace: jest.fn() }));
jest.mock('@/lib/api/customer-engagement', () => ({ getCustomerEngagementProgress: jest.fn() }));
jest.mock('@/lib/api/professionals', () => ({ getProfessionalDisclosure: jest.fn() }));
jest.mock('@/components/workbench/WorkbenchShell', () => ({
  WorkbenchShell: (props: { relationshipId: string; handoffToken?: string; copy: { title: string } }) => (
    <output data-testid="workbench">{`${props.relationshipId}|${props.handoffToken ?? 'none'}|${props.copy.title}`}</output>
  ),
}));
jest.mock('@/components/relationships/RelationshipWorkspace', () => ({
  RelationshipWorkspace: () => <output data-testid="legacy-workspace" />,
}));
jest.mock('@/components/relationships/RelationshipPreActivation', () => ({
  RelationshipPreActivation: (props: { availableSkills: unknown[] }) => (
    <output data-testid="pre-activation">{props.availableSkills.length}</output>
  ),
}));

const relationshipId = '0f5d4d3a-6f0c-4b6e-9f30-2d4f6a0c1b11';
const params = Promise.resolve({ relationshipId });

function resolved<T>(mock: unknown, value: unknown) {
  jest.mocked(mock as jest.MockedFunction<() => Promise<T>>).mockResolvedValue(value as T);
}

function arrange(state: string, workbench: Awaited<ReturnType<typeof getWorkbench>>, locale = 'en') {
  resolved(getServerAccessToken, 'token');
  resolved(getRequestI18n, { locale });
  resolved(getRelationship, { state, professionalType: 'NEUTRAL' });
  resolved(getRelationshipTimeline, {});
  resolved(getRelationshipEvaluation, {});
  resolved(getContractJourney, {});
  resolved(listEmploymentRelationships, { items: [] });
  resolved(getProfessionalDisclosure, { skills: [{ skillId: 'A' }] });
  resolved(getRelationshipWorkspaceViews, {});
  resolved(getEmploymentWorkspace, {});
  resolved(getCustomerEngagementProgress, {});
  jest.mocked(getWorkbench).mockResolvedValue(workbench);
}

describe('relationship page', () => {
  beforeEach(() => jest.clearAllMocks());

  it('sends a visitor without a session to sign in before reading anything', async () => {
    resolved(getServerAccessToken, undefined);

    await expect(RelationshipPage({ params })).rejects.toThrow('redirect:/login');
    expect(getRelationship).not.toHaveBeenCalled();
  });

  it('opens the workbench for an operating relationship and hands it the link token', async () => {
    arrange('ACTIVE', { state: 'available', snapshot: {} as never });

    render(await RelationshipPage({ params, searchParams: Promise.resolve({ handoff: 'h-token' }) }));

    expect(screen.getByTestId('workbench')).toHaveTextContent(`${relationshipId}|h-token|Workbench`);
    expect(screen.queryByTestId('legacy-workspace')).not.toBeInTheDocument();
    expect(getWorkbench).toHaveBeenCalledWith(relationshipId, 'token');
  });

  it('ignores a repeated handoff parameter and uses the customer language', async () => {
    arrange('TRIAL_ACTIVE', { state: 'available', snapshot: {} as never }, 'hi');

    render(await RelationshipPage({ params, searchParams: Promise.resolve({ handoff: ['a', 'b'] }) }));

    expect(screen.getByTestId('workbench')).toHaveTextContent(`${relationshipId}|none|वर्कबेंच`);
  });

  it.each([
    ['disabled', { state: 'disabled' as const }],
    ['unavailable', { state: 'unavailable' as const }],
  ])('falls back to the legacy workspace when the workbench is %s', async (_name, load) => {
    arrange('ACTIVE', load);

    render(await RelationshipPage({ params }));

    expect(screen.getByTestId('legacy-workspace')).toBeInTheDocument();
    expect(screen.queryByTestId('workbench')).not.toBeInTheDocument();
    expect(getRelationshipWorkspaceViews).toHaveBeenCalledWith(relationshipId, 'token');
  });

  it('shows the pre-activation journey with the skills of a configuring relationship and never reads the workbench', async () => {
    arrange('CONFIGURING', { state: 'available', snapshot: {} as never });

    render(await RelationshipPage({ params }));

    expect(screen.getByTestId('pre-activation')).toHaveTextContent('1');
    expect(getWorkbench).not.toHaveBeenCalled();
  });

  it('does not read the skill disclosure for a relationship that is neither configuring nor operating', async () => {
    arrange('PENDING', { state: 'available', snapshot: {} as never });

    render(await RelationshipPage({ params }));

    expect(screen.getByTestId('pre-activation')).toHaveTextContent('0');
    expect(getProfessionalDisclosure).not.toHaveBeenCalled();
  });
});
