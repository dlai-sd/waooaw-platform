import { render, screen, within } from '@testing-library/react';
import MyProfessionalsPage from '@/app/(authenticated)/professionals/mine/page';
import { getServerAccessToken } from '@/lib/server-auth';
import { listEmploymentRelationships } from '@/lib/api/relationships';

jest.mock('@/lib/server-auth', () => ({ getServerAccessToken: jest.fn() }));
jest.mock('@/lib/api/relationships', () => ({ listEmploymentRelationships: jest.fn() }));
jest.mock('@/lib/i18n-server', () => ({
  getRequestI18n: async () => ({ messages: {
    myExperts: 'My Experts', noProfessionalRelationships: 'No employed professionals yet.', returnHome: 'Return home',
  } }),
}));

const mockGetServerAccessToken = jest.mocked(getServerAccessToken);
const mockListEmploymentRelationships = jest.mocked(listEmploymentRelationships);

describe('MyProfessionalsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetServerAccessToken.mockResolvedValue('server-token');
  });

  it('renders each authoritative relationship as a separate expert workspace', async () => {
    mockListEmploymentRelationships.mockResolvedValue({ schemaVersion: '1.0.0', producedAt: new Date('2026-08-10T12:00:00Z'), items: [
        {
          relationshipId: 'relationship-1', agentInstanceId: 'agent-1', professionalDisplayName: 'Local growth expert',
          professionalType: 'DMA', lifecycleState: 'TRIAL_ACTIVE', currentGoalSummary: 'Grow leads',
          unreadState: 'NONE', availabilityState: 'AVAILABLE', currencyState: 'CURRENT',
          lastAuthoritativelyConfirmedAt: new Date('2026-08-10T10:00:00Z'),
          resumeTarget: { surface: 'CONVERSATION', relationshipId: 'relationship-1' },
        },
        {
          relationshipId: 'relationship-2', agentInstanceId: 'agent-2', professionalDisplayName: 'Retention expert',
          professionalType: 'DMA', lifecycleState: 'ACTIVE', currentGoalSummary: 'Improve renewals',
          unreadState: 'ACTION_REQUIRED', availabilityState: 'AVAILABLE', currencyState: 'CURRENT',
          lastAuthoritativelyConfirmedAt: new Date('2026-08-10T11:00:00Z'),
          resumeTarget: { surface: 'CONVERSATION', relationshipId: 'relationship-2' },
        },
    ] });

    render(await MyProfessionalsPage());

    expect(screen.getByRole('heading', { name: 'My Experts' })).toBeVisible();
    const experts = screen.getAllByRole('listitem');
    expect(experts).toHaveLength(2);
    expect(within(experts[0]).getByRole('link', { name: /Open workspace/ })).toHaveAttribute('href', '/relationships/relationship-1');
    expect(within(experts[1]).getByRole('link', { name: /Open workspace/ })).toHaveAttribute('href', '/relationships/relationship-2');
    expect(mockListEmploymentRelationships).toHaveBeenCalledWith('server-token');
  });

  it('shows an honest marketplace path when no relationship exists', async () => {
    mockListEmploymentRelationships.mockResolvedValue({ schemaVersion: '1.0.0', producedAt: new Date('2026-08-10T12:00:00Z'), items: [] });

    render(await MyProfessionalsPage());

    expect(screen.getByText('No employed professionals yet.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Browse professionals' })).toHaveAttribute('href', '/marketplace');
  });

  it('requires sign-in before reading employed professionals', async () => {
    mockGetServerAccessToken.mockResolvedValue(undefined);

    render(await MyProfessionalsPage());

    expect(screen.getByText('Sign in again to view your employed professionals.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
    expect(mockListEmploymentRelationships).not.toHaveBeenCalled();
  });

  it('does not invent experts when the authoritative relationship list fails', async () => {
    mockListEmploymentRelationships.mockRejectedValue(new Error('upstream unavailable'));

    render(await MyProfessionalsPage());

    expect(screen.getByText('Your authoritative relationship list could not be retrieved.')).toBeVisible();
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument();
  });
});