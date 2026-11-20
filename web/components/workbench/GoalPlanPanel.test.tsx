// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { WorkbenchSnapshot } from '@/lib/api/workbench-types';
import { workbenchMessages } from '@/lib/workbench-i18n';
import { GoalPlanPanel } from './GoalPlanPanel';
import { fakeResponse, present, relationshipId, snapshotFixture } from './workbench-test-data';

const copy = workbenchMessages('en');

const goalSummary = {
  goalId: 'goal-1',
  goalTypeId: 'grow',
  title: 'Grow reach',
  state: 'ACTIVE',
  currentVersion: 2,
  updatedAt: '2026-06-01T10:00:00Z',
};

function withGoalAndPlan(state: 'DRAFT' | 'READY_FOR_REVIEW'): WorkbenchSnapshot {
  const snapshot = snapshotFixture({
    goals: { schemaVersion: '1.0', items: [goalSummary] },
    plan: {
      schemaVersion: '1.0',
      planVersion: 'plan-3',
      state,
      goalRef: 'goal-1',
      milestones: [
        {
          milestoneId: 'm1',
          milestoneTypeId: 'launch',
          title: 'Launch',
          dueMeaning: 'End of month',
          state: 'PROPOSED',
        },
      ],
      calendar: [{ date: '2026-06-03T00:00:00Z', title: 'Review call' }],
      limitations: ['Results depend on posting frequency.'],
    },
  });
  snapshot.projection.currentGoalRef = 'goal-1';
  return snapshot;
}

function renderPanel(snapshot: WorkbenchSnapshot) {
  const onChanged = jest.fn(async () => undefined);
  render(<GoalPlanPanel copy={copy} onChanged={onChanged} relationshipId={relationshipId} snapshot={snapshot} />);
  return onChanged;
}

function captureFetch(responder: (url: string, init?: RequestInit) => Response) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), init });
    return responder(String(input), init);
  }) as jest.Mock;
  return calls;
}

describe('GoalPlanPanel', () => {
  afterEach(() => jest.restoreAllMocks());

  it('says so when there are no goals and no plan', () => {
    renderPanel(snapshotFixture({ plan: null }));
    expect(screen.getByText(copy.noGoals)).toBeInTheDocument();
    expect(screen.getByText(copy.noPlan)).toBeInTheDocument();
  });

  it('shows a goal unavailable instead of an empty list when the read failed', () => {
    renderPanel(snapshotFixture({ goals: null, plan: null }));
    expect(screen.getByText(copy.problems.WORKBENCH_UNAVAILABLE)).toBeInTheDocument();
  });

  it('loads the goal on demand and revises it with a reason', async () => {
    const calls = captureFetch((url) =>
      url.endsWith('/goals/goal-1')
        ? fakeResponse(200, {
            schemaVersion: '1.0',
            goal: goalSummary,
            parameters: { audience: 'local shops' },
            measures: [],
            constraints: [],
          })
        : fakeResponse(200, { schemaVersion: '1.0', status: 'ACCEPTED' })
    );
    const onChanged = renderPanel(withGoalAndPlan('DRAFT'));
    fireEvent.click(screen.getByRole('button', { name: copy.reviseGoal }));
    const reason = await screen.findByLabelText(copy.reasonForChange);
    expect(screen.getByLabelText('Audience')).toHaveValue('local shops');
    fireEvent.change(screen.getByLabelText(copy.goalName), { target: { value: 'Grow reach faster' } });
    fireEvent.change(reason, { target: { value: 'New season' } });
    fireEvent.click(screen.getAllByRole('button', { name: copy.reviseGoal })[1]);
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    const post = present(calls.find((call) => call.init?.method === 'POST'));
    expect(post.url).toBe(`/api/relationships/${relationshipId}/workbench/goals/goal-1/revisions`);
    expect(JSON.parse(String(post.init?.body))).toEqual({
      schemaVersion: '1.0',
      expectedVersion: 'relationship-7',
      title: 'Grow reach faster',
      parameters: { audience: 'local shops' },
      reason: 'New season',
    });
  });

  it('reports a goal that could not be loaded', async () => {
    captureFetch(() => fakeResponse(503, { code: 'WORKBENCH_UNAVAILABLE' }));
    renderPanel(withGoalAndPlan('DRAFT'));
    fireEvent.click(screen.getByRole('button', { name: copy.reviseGoal }));
    expect(await screen.findByRole('alert')).toHaveTextContent(copy.problems.WORKBENCH_UNAVAILABLE);
  });

  it('proposes the drafted plan for review against the current goal', async () => {
    const calls = captureFetch(() => fakeResponse(200, { schemaVersion: '1.0', status: 'ACCEPTED' }));
    const onChanged = renderPanel(withGoalAndPlan('DRAFT'));
    expect(screen.getByText('Results depend on posting frequency.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.proposePlan }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({
      schemaVersion: '1.0',
      expectedVersion: 'relationship-7',
      goalId: 'goal-1',
      milestones: [{ milestoneTypeId: 'launch', title: 'Launch' }],
    });
    expect(calls[0].url).toBe(`/api/relationships/${relationshipId}/workbench/plans`);
  });

  it('only lets the plan be agreed after the limits are acknowledged', async () => {
    const calls = captureFetch(() => fakeResponse(200, { schemaVersion: '1.0', status: 'ACCEPTED' }));
    renderPanel(withGoalAndPlan('READY_FOR_REVIEW'));
    const agree = screen.getByRole('button', { name: copy.agreePlan });
    expect(agree).toBeDisabled();
    fireEvent.click(screen.getByLabelText(copy.acknowledgeLimits));
    expect(agree).toBeEnabled();
    fireEvent.click(agree);
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].url).toBe(`/api/relationships/${relationshipId}/workbench/plans/plan-3/accept`);
    expect(JSON.parse(String(calls[0].init?.body))).toMatchObject({ acknowledgedLimitations: true });
  });
});
