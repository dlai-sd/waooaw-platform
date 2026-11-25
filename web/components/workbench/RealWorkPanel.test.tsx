// Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R005, WC170-R006, WC170-R007, WC170-R008, WC170-R010
// Constitutional basis: C-001, C-049, C-059, C-076

import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { RealWorkPanel, RealWorkView, decide } from './RealWorkPanel';
import type { ArtifactStatus, RealWorkArtifactItem, RealWorkSnapshot } from '@/lib/api/real-work-types';
import { realWorkCopy as copy } from '@/lib/real-work-copy';

const relationshipId = '0f5d4d3a-6f0c-4b6e-9f30-2d4f6a0c1b11';
const digest = 'a'.repeat(64);

function artifact(
  status: ArtifactStatus,
  approved: boolean,
  scoped: boolean,
  overrides: Record<string, unknown> = {}
): RealWorkArtifactItem {
  return {
    artifact: {
      artifactId: '11111111-1111-4111-8111-111111111111',
      artifactType: 'CAMPAIGN_BRIEF',
      version: 2,
      digest,
      status,
      plainLanguageSummary: 'Grow weekend bookings.',
      limitations: ['Seen on public pages only.'],
      authorityBoundary: 'I may draft; only you can approve publication.',
      ...overrides,
    } as RealWorkArtifactItem['artifact'],
    decisions: {
      approval: approved ? { kind: 'APPROVAL', evidenceId: 'e1', decidedAt: '2026-11-25T00:00:00Z' } : null,
      scopeConfirmation: scoped
        ? { kind: 'SCOPE_CONFIRMATION', evidenceId: 'e2', decidedAt: '2026-11-25T00:00:00Z' }
        : null,
      executable: approved && scoped,
      blockedReason: null,
    },
  };
}

function snapshot(overrides: Partial<RealWorkSnapshot> = {}): RealWorkSnapshot {
  return {
    artifacts: {
      commandContext: { workspaceVersion: 'w1', manifestVersion: 'm1', decisionSpaceVersion: 3 },
      items: [artifact('PROPOSED', false, false)],
    },
    timeline: {
      relationshipId,
      emergencyStopActive: false,
      events: [],
      workItems: [
        {
          workItemId: 'w-1',
          workItemType: 'SOCIAL_POST',
          state: 'EXECUTING',
          reasonCode: 'AWAITING_PROVIDER_PROOF',
          sentence: 'The social post was accepted. It counts as done only when the provider confirms it.',
          events: [
            {
              eventId: 'ev-1',
              workItemId: 'w-1',
              workItemType: 'SOCIAL_POST',
              state: 'EXECUTING',
              evidenceRefs: ['receipt:1'],
              occurredAt: '2026-11-25T00:00:00Z',
              sequence: 1,
              sentence: 'The agent is working on the social post.',
            },
          ],
        },
      ],
    },
    outcomes: {
      relationshipId,
      activity: [
        {
          claimId: 'ACTIVITY:SOCIAL_POST',
          measureId: 'SOCIAL_POST',
          claimText: '4 social post completed',
          category: 'ACTIVITY',
          derivation: 'INDEPENDENT',
          unit: 'ITEMS',
          asOf: '2026-11-25T00:00:00Z',
          workItemIds: ['w-1'],
          evidenceIds: ['ev-123'],
          limitations: ['Counts completed work. It is activity, not a business result.'],
        },
      ],
      outcomes: [],
      agentStated: [
        {
          claimId: 'reach',
          measureId: 'REACH',
          claimText: 'Reach rose by 40 percent',
          category: 'ACTIVITY',
          derivation: 'AGENT_STATED',
          label: 'Stated by the agent. Not independently verified.',
          unit: 'PERCENT',
          asOf: '2026-11-25T00:00:00Z',
          workItemIds: ['w-1'],
          evidenceIds: ['ev-9'],
          limitations: [],
        },
      ],
      notMeasurableYet: [{ measureId: 'QUALIFIED_ENQUIRIES', text: 'Not measurable yet' }],
      withheldClaims: 2,
    },
    ...overrides,
  };
}

function view(value: RealWorkSnapshot, onDecide = jest.fn(), busy = false, message = '') {
  render(<RealWorkView busy={busy} message={message} onDecide={onDecide} snapshot={value} />);
  return onDecide;
}

describe('RealWorkView decisions', () => {
  it('shows two separate steps in order and enables only the first until the version is approved', () => {
    const onDecide = view(snapshot());
    const steps = within(screen.getByRole('list', { name: copy.decisionsTitle })).getAllByRole('listitem');
    expect(steps[0]).toHaveTextContent(copy.stepApprove);
    expect(steps[1]).toHaveTextContent(copy.stepScope);
    expect(screen.getByRole('button', { name: copy.approveAction })).toBeEnabled();
    expect(screen.getByRole('button', { name: copy.scopeAction })).toBeDisabled();
    expect(screen.getByText('Grow weekend bookings.')).toBeInTheDocument();
    expect(screen.getByText('Seen on public pages only.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.approveAction }));
    expect(onDecide).toHaveBeenCalledWith(
      'ACCEPT_ARTIFACT_VERSION',
      expect.objectContaining({ decisions: expect.anything() })
    );
  });

  it('opens the boundary step after approval and says when both are done', () => {
    const onDecide = view({
      ...snapshot(),
      artifacts: {
        commandContext: null,
        items: [artifact('LOCKED', true, false)],
      },
    });
    expect(screen.getByRole('button', { name: copy.approveAction })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: copy.scopeAction }));
    expect(onDecide).toHaveBeenCalledWith('CONFIRM_SCOPE_BOUNDARY', expect.anything());
  });

  it('says the agent may work only when both steps exist for the version', () => {
    view({ ...snapshot(), artifacts: { commandContext: null, items: [artifact('LOCKED', true, true)] } });
    expect(screen.getByText(copy.executable)).toBeInTheDocument();
  });

  it('shows a replaced version as unusable and offers no decision', () => {
    view({ ...snapshot(), artifacts: { commandContext: null, items: [artifact('SUPERSEDED', true, true)] } });
    expect(screen.getByText(copy.replaced)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: copy.approveAction })).not.toBeInTheDocument();
  });

  it('says plainly when nothing is waiting and hides drafts', () => {
    view({ ...snapshot(), artifacts: { commandContext: null, items: [artifact('DRAFT', false, false)] } });
    expect(screen.getByText(copy.noDecisions)).toBeInTheDocument();
  });
});

describe('RealWorkView timeline and results', () => {
  it('shows one plain sentence per work item with its state and its events behind a details control', () => {
    view(snapshot());
    expect(screen.getByText(copy.states.EXECUTING)).toBeInTheDocument();
    expect(screen.getAllByText(/counts as done only when the provider confirms it/).length).toBeGreaterThan(0);
    expect(screen.getByText(copy.evidenceCount(1))).toBeInTheDocument();
  });

  it('shows the Emergency Stop banner and an empty timeline plainly', () => {
    view({
      ...snapshot(),
      timeline: { relationshipId, events: [], workItems: [], emergencyStopActive: true },
    });
    expect(screen.getByRole('alert')).toHaveTextContent(copy.stopActive);
    expect(screen.getByText(copy.noTimeline)).toBeInTheDocument();
  });

  it('keeps work completed apart from business results and labels what the agent states', () => {
    view(snapshot());
    expect(screen.getByText('4 social post completed')).toBeInTheDocument();
    expect(screen.getByText(copy.activityNote)).toBeInTheDocument();
    expect(screen.getByText('Reach rose by 40 percent')).toBeInTheDocument();
    expect(screen.getByText(/Stated by the agent/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`Qualified enquiries: ${copy.notMeasurable}`))).toBeInTheDocument();
    expect(screen.getByText(copy.withheld(2))).toBeInTheDocument();
  });

  it('traces a claim to the work and evidence behind it', () => {
    view(snapshot());
    expect(screen.getAllByText(copy.workBehind).length).toBeGreaterThan(0);
    expect(screen.getByText('ev-123')).toBeInTheDocument();
  });

  it('says an unreadable section is unavailable instead of showing it as empty', () => {
    view({ artifacts: null, timeline: null, outcomes: null });
    expect(screen.getAllByText(copy.unavailable)).toHaveLength(3);
    expect(screen.queryByText(copy.noTimeline)).not.toBeInTheDocument();
    expect(screen.queryByText(copy.noDecisions)).not.toBeInTheDocument();
  });

  it('tells the customer plainly when there is nothing yet', () => {
    view({
      artifacts: { commandContext: null, items: [] },
      timeline: { relationshipId, events: [], workItems: [], emergencyStopActive: false },
      outcomes: {
        relationshipId,
        activity: [],
        outcomes: [],
        agentStated: [],
        notMeasurableYet: [],
        withheldClaims: 0,
      },
    });
    expect(screen.getByText(copy.noDecisions)).toBeInTheDocument();
    expect(screen.getByText(copy.noTimeline)).toBeInTheDocument();
    expect(screen.getByText(copy.noResults)).toBeInTheDocument();
  });

  it('lets the customer see every detail and the fingerprint of the exact version they approve', () => {
    view({
      ...snapshot(),
      artifacts: {
        commandContext: null,
        items: [artifact('PROPOSED', false, false, { content: { goal: 'Grow weekend bookings by 20 percent' } })],
      },
    });
    expect(screen.getByText(copy.seeEveryDetail)).toBeInTheDocument();
    expect(screen.getByText(/Grow weekend bookings by 20 percent/)).toBeInTheDocument();
    expect(screen.getByText('a'.repeat(12))).toBeInTheDocument();
  });

  it('announces a message from a refused decision', () => {
    view(snapshot(), jest.fn(), false, copy.strongSignIn);
    expect(screen.getByText(copy.strongSignIn)).toBeInTheDocument();
  });
});

describe('decide', () => {
  const item = artifact('PROPOSED', false, false) as never;
  const context = { workspaceVersion: 'w1', manifestVersion: 'm1', decisionSpaceVersion: 3 };

  afterEach(() => jest.restoreAllMocks());

  it('posts the exact artifact id and digest with a fresh idempotency key', async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: true, status: 202, json: async () => ({ state: 'ACCEPTED' }) });
    global.fetch = fetchMock as never;
    expect(await decide(relationshipId, 'ACCEPT_ARTIFACT_VERSION', item, context)).toBe('ok');
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body).toMatchObject({ kind: 'ACCEPT_ARTIFACT_VERSION', artifactDigest: digest, commandContext: context });
    expect(body.idempotencyKey).toMatch(/^[0-9a-f-]{36}$/);
  });

  it('maps a refused strong sign-in, a blocked outcome and a network failure', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 403, json: async () => ({}) }) as never;
    expect(await decide(relationshipId, 'ACCEPT_ARTIFACT_VERSION', item, context)).toBe('strong-sign-in');
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => ({ state: 'BLOCKED' }) }) as never;
    expect(await decide(relationshipId, 'CONFIRM_SCOPE_BOUNDARY', item, context)).toBe('failed');
    global.fetch = jest.fn().mockRejectedValue(new Error('offline')) as never;
    expect(await decide(relationshipId, 'CONFIRM_SCOPE_BOUNDARY', item, context)).toBe('failed');
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }) as never;
    expect(await decide(relationshipId, 'CONFIRM_SCOPE_BOUNDARY', item, context)).toBe('failed');
  });
});

describe('RealWorkPanel', () => {
  afterEach(() => jest.restoreAllMocks());

  it('loads the record and reloads it after a decision', async () => {
    const calls: string[] = [];
    global.fetch = jest.fn(async (_url: string, init?: RequestInit) => {
      calls.push(init?.method ?? 'GET');
      return {
        ok: true,
        status: 200,
        json: async () => (init?.method === 'POST' ? { state: 'ACCEPTED' } : snapshot()),
      };
    }) as never;
    render(<RealWorkPanel relationshipId={relationshipId} />);
    expect(screen.getByText(copy.loading)).toBeInTheDocument();
    const approve = await screen.findByRole('button', { name: copy.approveAction });
    await act(async () => {
      fireEvent.click(approve);
    });
    await waitFor(() => expect(calls).toEqual(['GET', 'POST', 'GET']));
  });

  it('says plainly when the record cannot be read and when strong sign-in is needed', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }) as never;
    const { unmount } = render(<RealWorkPanel relationshipId={relationshipId} />);
    expect(await screen.findByText(copy.unavailable)).toBeInTheDocument();
    unmount();

    global.fetch = jest.fn(async (_url: string, init?: RequestInit) =>
      init?.method === 'POST'
        ? { ok: false, status: 403, json: async () => ({}) }
        : { ok: true, status: 200, json: async () => snapshot() }
    ) as never;
    render(<RealWorkPanel relationshipId={relationshipId} />);
    const approve = await screen.findByRole('button', { name: copy.approveAction });
    await act(async () => {
      fireEvent.click(approve);
    });
    expect(await screen.findByText(copy.strongSignIn)).toBeInTheDocument();
  });

  it('uses a snapshot it was given without fetching', () => {
    global.fetch = jest.fn() as never;
    render(<RealWorkPanel initial={snapshot()} relationshipId={relationshipId} />);
    expect(global.fetch).not.toHaveBeenCalled();
    expect(screen.getByText('Grow weekend bookings.')).toBeInTheDocument();
  });
});
