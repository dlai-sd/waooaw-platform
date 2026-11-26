// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R017, R018, R020, R021, R022, R028, R029
// Constitutional basis: C-001, C-023, C-059, C-063

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { operationMessages } from '@/lib/operation-i18n';
import { ConversationDock } from './ConversationDock';
import { ApprovalsView, ImproveView, PublishedView, ResultsView } from './OperationsViews';
import { type FetchCall, installOperationFetch, item, platforms, refused, relationshipId } from './operation-test-data';

const copy = operationMessages('en');
const connected = [{ ...platforms()[0], presence: 'CONNECTED_TESTED', canConnect: false }, platforms()[1]];

describe('ApprovalsView', () => {
  afterEach(() => jest.restoreAllMocks());

  const content = item({
    itemId: 'c1',
    kind: 'CONTENT',
    title: 'Festival post',
    isSuggestion: false,
    state: 'PROPOSED',
    platformId: 'FACEBOOK',
    startDate: null,
  });
  const approved = item({
    itemId: 'c2',
    kind: 'CONTENT',
    title: 'Approved post',
    isSuggestion: false,
    isApproved: true,
    authorState: 'APPROVED_VERSION',
    state: 'APPROVED',
    startDate: null,
  });

  it('lists what waits for approval and what is approved and ready to schedule', async () => {
    installOperationFetch([
      ['GET items', (call: FetchCall) => (call.path.endsWith('CONTENT') ? [content, approved] : [])],
    ]);
    render(
      <ApprovalsView
        copy={copy}
        onChanged={jest.fn()}
        platforms={connected}
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );

    expect(await screen.findByRole('button', { name: 'Festival post' })).toBeInTheDocument();
    expect(screen.getByRole('form', { name: `${copy.schedule}: Approved post` })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Festival post' }));
    expect(await screen.findByRole('button', { name: copy.approve })).toBeInTheDocument();
  });

  it('approves the version shown and reloads', async () => {
    const calls = installOperationFetch([
      ['GET items', (call: FetchCall) => (call.path.endsWith('CONTENT') ? [content] : [])],
      ['POST items/c1/approve', item({ itemId: 'c1', isApproved: true })],
    ]);
    const onChanged = jest.fn();
    render(
      <ApprovalsView
        copy={copy}
        onChanged={onChanged}
        platforms={connected}
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Festival post' }));
    fireEvent.click(await screen.findByRole('button', { name: copy.approve }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(calls.some((call) => call.path === 'items/c1/approve')).toBe(true);
  });

  it('schedules an approved post on a chosen platform and day', async () => {
    const calls = installOperationFetch([
      ['GET items', (call: FetchCall) => (call.path.endsWith('CONTENT') ? [approved] : [])],
      ['POST schedule', item({ kind: 'SLOT' })],
    ]);
    const onChanged = jest.fn();
    render(
      <ApprovalsView
        copy={copy}
        onChanged={onChanged}
        platforms={connected}
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );
    const form = await screen.findByRole('form', { name: `${copy.schedule}: Approved post` });

    fireEvent.change(form.querySelector('select') as HTMLSelectElement, { target: { value: 'FACEBOOK' } });
    fireEvent.change(form.querySelector('input[type="date"]') as HTMLInputElement, { target: { value: '2026-12-05' } });
    fireEvent.click(screen.getByRole('button', { name: copy.schedule }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(calls.find((call) => call.path === 'schedule')?.body).toEqual({
      contentId: 'c2',
      platformId: 'FACEBOOK',
      date: '2026-12-05',
      route: 'TOOL',
    });
  });

  it('explains a gate in plain words and links to the mode that fixes it', async () => {
    installOperationFetch([
      ['GET items', (call: FetchCall) => (call.path.endsWith('CONTENT') ? [approved] : [])],
      [
        'POST schedule',
        refused(
          409,
          'OPERATION_GATE_BLOCKED',
          'Finish this first: Confirm what I understood about your business.',
          'INDUCT'
        ),
      ],
    ]);
    const onGoMode = jest.fn();
    render(
      <ApprovalsView
        copy={copy}
        onChanged={jest.fn()}
        onGoMode={onGoMode}
        platforms={connected}
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );
    const form = await screen.findByRole('form', { name: `${copy.schedule}: Approved post` });
    fireEvent.change(form.querySelector('input[type="date"]') as HTMLInputElement, { target: { value: '2026-12-05' } });
    fireEvent.change(form.querySelector('select') as HTMLSelectElement, { target: { value: 'FACEBOOK' } });
    fireEvent.click(screen.getByRole('button', { name: copy.schedule }));

    expect(await screen.findByText(/Finish this first/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.goToMode }));
    expect(onGoMode).toHaveBeenCalledWith('INDUCT');
  });

  it('says when nothing waits and offers a retry when the read failed', async () => {
    installOperationFetch([['GET items', []]]);
    const { unmount } = render(
      <ApprovalsView
        copy={copy}
        onChanged={jest.fn()}
        platforms={connected}
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );
    expect((await screen.findAllByText(copy.nothingYet)).length).toBe(2);
    unmount();

    installOperationFetch([['GET items', refused(503, 'X', 'down')]]);
    render(
      <ApprovalsView
        copy={copy}
        onChanged={jest.fn()}
        platforms={connected}
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    installOperationFetch([['GET items', []]]);
    fireEvent.click(screen.getByRole('button', { name: copy.retry }));
    expect((await screen.findAllByText(copy.nothingYet)).length).toBe(2);
  });
});

describe('PublishedView', () => {
  afterEach(() => jest.restoreAllMocks());

  const slots = [
    item({
      itemId: 's1',
      kind: 'SLOT',
      title: 'Post one',
      state: 'SCHEDULED',
      isSuggestion: false,
      startDate: '2026-12-05',
    }),
    item({
      itemId: 's2',
      kind: 'SLOT',
      title: 'Post two',
      state: 'PUBLISHED',
      isSuggestion: false,
      startDate: '2026-12-03',
    }),
  ];

  it('grants a separate publishing permission and publishes only a scheduled post', async () => {
    const calls = installOperationFetch([
      ['GET items', slots],
      ['PUT publish-authority', { granted: true }],
      ['POST slots/s1/publish', item({ kind: 'SLOT', state: 'PUBLISHED' })],
    ]);
    const onChanged = jest.fn();
    render(
      <PublishedView
        copy={copy}
        onChanged={onChanged}
        publishAuthority={false}
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );

    expect(await screen.findByText(/Post one/)).toBeInTheDocument();
    expect(screen.getByText(/Post one/).closest('li')).toHaveTextContent('Scheduled');
    expect(screen.getAllByRole('button', { name: copy.publishNow })).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: copy.grantPublish }));
    await waitFor(() =>
      expect(calls.some((call) => call.path === 'publish-authority' && call.body?.granted === true)).toBe(true)
    );
    fireEvent.click(screen.getByRole('button', { name: copy.publishNow }));
    await waitFor(() => expect(calls.some((call) => call.path === 'slots/s1/publish')).toBe(true));
    expect(onChanged).toHaveBeenCalledTimes(2);
  });

  it('shows the plain reason a post was not published and the way to fix it', async () => {
    installOperationFetch([
      ['GET items', slots],
      [
        'POST slots/',
        refused(
          409,
          'OPERATION_ACCOUNT_NOT_CONNECTED',
          'Facebook needs to be reconnected. Nothing was published.',
          'INDUCT'
        ),
      ],
      [
        'PUT publish-authority',
        refused(403, 'OPERATION_STEP_UP_REQUIRED', 'A fresh strong sign-in is required for this action.'),
      ],
    ]);
    const onGoMode = jest.fn();
    render(
      <PublishedView
        copy={copy}
        onChanged={jest.fn()}
        onGoMode={onGoMode}
        publishAuthority
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );

    fireEvent.click(await screen.findByRole('button', { name: copy.revokePublish }));
    expect(await screen.findByText(/fresh strong sign-in/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.publishNow }));
    expect(await screen.findByText(/Nothing was published/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.goToMode }));
    expect(onGoMode).toHaveBeenCalledWith('INDUCT');
  });

  it('handles an empty list and a failed read', async () => {
    installOperationFetch([['GET items', []]]);
    const { unmount } = render(
      <PublishedView
        copy={copy}
        onChanged={jest.fn()}
        publishAuthority
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );
    expect(await screen.findByText(copy.nothingYet)).toBeInTheDocument();
    unmount();
    installOperationFetch([['GET items', refused(503, 'X', 'down')]]);
    render(
      <PublishedView
        copy={copy}
        onChanged={jest.fn()}
        publishAuthority
        refreshKey={0}
        relationshipId={relationshipId}
      />
    );
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('ResultsView and ImproveView', () => {
  afterEach(() => jest.restoreAllMocks());

  const digest = item({
    itemId: 'd1',
    kind: 'DIGEST',
    title: '2026-12 digest',
    body: 'Do more of the festival posts.',
    state: 'PROPOSED',
    updatedAt: '2026-12-31T00:00:00Z',
    payload: {
      request: 'Share last month’s enquiry count.',
      rows: [
        { skillId: 'SKILL_ONE', baseline: '0', current: '4 posts', source: 'Owner record', freshness: 'today' },
        { skillId: 'SKILL_TWO', baseline: null, current: null, howToMeasure: 'Connect a source that records it.' },
      ],
    },
  });
  const older = item({
    itemId: 'd0',
    kind: 'DIGEST',
    title: 'older',
    state: 'ACCEPTED',
    updatedAt: '2026-11-30T00:00:00Z',
    payload: {},
  });

  it('shows results against each goal with its source and freshness, and says "not measured" with how to measure', async () => {
    installOperationFetch([['GET items', [older, digest]]]);
    render(
      <ResultsView copy={copy} labels={{ SKILL_ONE: 'Profile' }} refreshKey={0} relationshipId={relationshipId} />
    );

    expect(await screen.findByRole('row', { name: /Profile/ })).toHaveTextContent('4 posts');
    expect(screen.getByRole('row', { name: /Skill two/ })).toHaveTextContent('Not measured');
    expect(screen.getByText(/Connect a source that records it/)).toBeInTheDocument();
    expect(screen.getByText(/today/)).toBeInTheDocument();
  });

  it('says when there are no results yet and when the read failed', async () => {
    installOperationFetch([['GET items', []]]);
    const { unmount } = render(<ResultsView copy={copy} labels={{}} refreshKey={0} relationshipId={relationshipId} />);
    expect(await screen.findByText(copy.nothingYet)).toBeInTheDocument();
    unmount();
    installOperationFetch([['GET items', refused(503, 'X', 'down')]]);
    render(<ResultsView copy={copy} labels={{}} refreshKey={0} relationshipId={relationshipId} />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('turns an accepted recommendation into decisions and never applies one on its own', async () => {
    const calls = installOperationFetch([
      ['GET items', [digest, older]],
      ['POST digests/d1/decision', item({ kind: 'DIGEST', state: 'ACCEPTED' })],
    ]);
    const onChanged = jest.fn();
    render(<ImproveView copy={copy} onChanged={onChanged} refreshKey={0} relationshipId={relationshipId} />);

    expect(await screen.findByText('Do more of the festival posts.')).toBeInTheDocument();
    expect(screen.getByText(/enquiry count/)).toBeInTheDocument();
    expect(screen.getByText('Accepted')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.acceptDigest }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(calls.find((call) => call.method === 'POST')?.body).toEqual({ accept: true, route: 'TOOL' });
  });

  it('shows a refused decision, an empty list and a failed read', async () => {
    installOperationFetch([
      ['GET items', [digest]],
      ['POST digests/', refused(404, 'OPERATION_ITEM_NOT_FOUND', 'That item was not found.')],
    ]);
    const { unmount } = render(
      <ImproveView copy={copy} onChanged={jest.fn()} refreshKey={0} relationshipId={relationshipId} />
    );
    fireEvent.click(await screen.findByRole('button', { name: copy.declineDigest }));
    expect(await screen.findByText('That item was not found.')).toBeInTheDocument();
    unmount();

    installOperationFetch([['GET items', []]]);
    const second = render(
      <ImproveView copy={copy} onChanged={jest.fn()} refreshKey={0} relationshipId={relationshipId} />
    );
    expect(await screen.findByText(copy.nothingYet)).toBeInTheDocument();
    second.unmount();
    installOperationFetch([['GET items', refused(503, 'X', 'down')]]);
    render(<ImproveView copy={copy} onChanged={jest.fn()} refreshKey={0} relationshipId={relationshipId} />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('ConversationDock', () => {
  afterEach(() => jest.restoreAllMocks());

  const step = {
    modeId: 'INDUCT' as const,
    textKey: 'K',
    text: 'Confirm what I understood about your business.',
    primaryLabel: 'Confirm profile',
    command: 'CONFIRM_LABELS',
  };
  const chats = { allowed: 1000, used: 10, remaining: 990, reached: false };

  function renderDock(overrides = {}) {
    const handlers = { onAct: jest.fn(), onChats: jest.fn() };
    render(
      <ConversationDock
        chats={chats}
        copy={copy}
        next={step}
        readinessLine="3 of 17 items confirmed"
        relationshipId={relationshipId}
        stopped={false}
        {...handlers}
        {...overrides}
      />
    );
    return handlers;
  }

  it('opens with the one next step in the same words as the readiness line and shows what is left of the allowance', () => {
    const { onAct } = renderDock();

    expect(screen.getByText(step.text)).toBeInTheDocument();
    expect(screen.getByText('990')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: step.primaryLabel }));
    fireEvent.click(screen.getByRole('button', { name: copy.letMeDoIt }));
    expect(onAct).toHaveBeenCalledWith(step, 'TOOL');
    fireEvent.click(screen.getByRole('button', { name: copy.explain }));
    expect(screen.getByText(/3 of 17 items confirmed/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.explain }));
    expect(screen.queryByText(/3 of 17 items confirmed/)).not.toBeInTheDocument();
  });

  it('counts "Do it for me" as one conversation and then acts the same way the tools do', async () => {
    const calls = installOperationFetch([['POST conversation/chats', { ...chats, used: 11, remaining: 989 }]]);
    const { onAct, onChats } = renderDock();

    fireEvent.click(screen.getByRole('button', { name: copy.doItForMe }));

    await waitFor(() => expect(onAct).toHaveBeenCalledWith(step, 'ASKED'));
    expect(onChats).toHaveBeenCalledWith(expect.objectContaining({ remaining: 989 }));
    expect(calls).toHaveLength(1);
  });

  it('explains the limit plainly and does not act when the allowance is used up', async () => {
    installOperationFetch([['POST conversation/chats', refused(409, 'OPERATION_CHAT_ALLOWANCE_REACHED', 'x')]]);
    const { onAct } = renderDock();

    fireEvent.click(screen.getByRole('button', { name: copy.doItForMe }));

    expect(await screen.findByText(copy.chatLimit)).toBeInTheDocument();
    expect(onAct).not.toHaveBeenCalled();
  });

  it('shows another refusal in plain words and a reached allowance as disabled', async () => {
    installOperationFetch([
      ['POST conversation/chats', refused(503, 'OPERATION_UNAVAILABLE', 'The service did not answer.')],
    ]);
    renderDock();
    fireEvent.click(screen.getByRole('button', { name: copy.doItForMe }));
    expect(await screen.findByText('The service did not answer.')).toBeInTheDocument();
  });

  it('disables "Do it for me" at the limit and when stopped, says everything is in order when there is no next step, and opens the conversation', () => {
    const open = jest.fn();
    window.addEventListener('waooaw:open-conversation', open);
    renderDock({ chats: { ...chats, remaining: 0, reached: true }, stopped: true });

    expect(screen.getByRole('button', { name: copy.doItForMe })).toBeDisabled();
    expect(screen.getByText(copy.chatLimit)).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent(copy.stoppedBanner);
    fireEvent.click(screen.getByRole('button', { name: copy.askPlaceholder }));
    expect(open).toHaveBeenCalled();
    window.removeEventListener('waooaw:open-conversation', open);
  });

  it('says everything is in order when there is no next step', () => {
    renderDock({ next: null });
    expect(screen.getByText(copy.allDone)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: copy.doItForMe })).not.toBeInTheDocument();
  });
});
