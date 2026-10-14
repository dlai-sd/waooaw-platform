import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { CustomerEngagementProgressV1 } from '@/lib/api/generated/models/CustomerEngagementProgressV1';
import type { WorkspaceFocusRefV1 } from '@/lib/api/generated/models/WorkspaceFocusRefV1';
import { CustomerEngagementWorkspace } from './CustomerEngagementWorkspace';

const push = jest.fn();
const refresh = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push, refresh }),
}));

const focus: WorkspaceFocusRefV1 = {
  schemaVersion: '1',
  focusToken: 'protected-focus-token-value',
  destination: 'OPERATION' as const,
  label: 'operations',
  accessibleLabel: 'Open operations for this professional relationship',
  issuedAt: new Date('2026-01-01T00:00:00Z'),
  expiresAt: new Date('2026-01-01T00:15:00Z'),
};

const progress: CustomerEngagementProgressV1 = {
  schemaVersion: '1',
  relationshipId: '00000000-0000-0000-0000-000000000121',
  projectionVersion: 'projection-1',
  projectionContractVersion: 'cew-progress-1',
  generatedAt: new Date('2026-01-01T00:00:00Z'),
  projectionSources: [],
  lifecycleStage: 'OPERATIONS',
  headline: 'Track work and customer outcomes',
  summary: 'Progress is composed from current owner-confirmed relationship truth.',
  items: [
    {
      itemId: 'lifecycle:121',
      title: 'Employment journey',
      state: 'WORKING',
      owner: 'CUSTOMER',
      required: true,
      truth: {
        delivery: 'UNKNOWN',
        processing: 'WORKING',
        evidence: 'COMPLETED',
        commercial: 'UNKNOWN',
        outcome: 'UNKNOWN',
      },
      provenance: {
        sourceOwner: 'RELATIONSHIP',
        sourceSubjectRef: 'relationship-121',
        sourceVersion: 'relationship-3',
        sourceContractVersion: 'ae01-relationship-1',
        producedAt: new Date('2026-01-01T00:00:00Z'),
        lastAuthoritativeConfirmationAt: new Date('2026-01-01T00:00:00Z'),
        freshness: 'CURRENT',
        evidenceState: 'RECORDED',
      },
      updatedAt: new Date('2026-01-01T00:00:00Z'),
      nextAction: { actionType: 'OPEN', label: 'Review current work', focus },
    },
  ],
  availableFocuses: [focus],
};

describe('CustomerEngagementWorkspace', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(global, 'fetch', {
      configurable: true,
      value: jest.fn(),
      writable: true,
    });
  });

  it('renders all five truth dimensions and resolves protected focus before navigation', async () => {
    jest.mocked(global.fetch).mockResolvedValueOnce({
      json: async () => ({
        canonicalRoute: '/relationships/00000000-0000-0000-0000-000000000121#operations',
      }),
      ok: true,
      status: 200,
    } as Response);

    render(<CustomerEngagementWorkspace progress={progress} />);

    expect(screen.getByText('Delivery: unknown')).toBeInTheDocument();
    expect(screen.getByText('Processing: working')).toBeInTheDocument();
    expect(screen.getByText('Evidence: completed')).toBeInTheDocument();
    expect(screen.getByText('Commercial: unknown')).toBeInTheDocument();
    expect(screen.getByText('Outcome: unknown')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Review current work' }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith('/relationships/00000000-0000-0000-0000-000000000121#operations')
    );
    expect(fetch).toHaveBeenCalledWith(
      '/api/relationships/00000000-0000-0000-0000-000000000121/focus-resolutions',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('keeps focus in place and announces an unresolved destination', async () => {
    jest.mocked(global.fetch).mockResolvedValueOnce({
      json: async () => ({ title: 'Relationship context changed. Refresh progress.' }),
      ok: false,
      status: 409,
    } as Response);

    render(<CustomerEngagementWorkspace progress={progress} />);
    fireEvent.click(screen.getByRole('button', { name: 'Review current work' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Relationship context changed. Refresh progress.');
    expect(push).not.toHaveBeenCalled();
  });

  it('refreshes the projection and fails closed when focus resolution is malformed', async () => {
    jest.mocked(global.fetch).mockResolvedValueOnce({
      json: jest.fn().mockRejectedValue(new Error('invalid response')),
      ok: false,
      status: 502,
    } as unknown as Response);

    render(<CustomerEngagementWorkspace progress={progress} />);
    fireEvent.click(screen.getByRole('button', { name: 'Refresh current progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'operations' }));

    expect(refresh).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This destination cannot be confirmed. Refresh progress before trying again.'
    );
    expect(push).not.toHaveBeenCalled();
  });
});
