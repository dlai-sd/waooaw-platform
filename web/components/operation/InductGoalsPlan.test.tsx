// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R008, R010, R013, R014, R015
// Constitutional basis: C-001, C-023, C-048, C-059, C-063, C-083

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { operationMessages } from '@/lib/operation-i18n';
import { GoalsView } from './GoalsView';
import { PlatformsView, ProfileView } from './InductViews';
import { PlanTreeBlock } from './PlanTreeBlock';
import { installOperationFetch, item, platforms, refused, relationshipId } from './operation-test-data';

const copy = operationMessages('en');
const levels = [
  { levelId: 'LEVEL_ONE', labelKey: 'L1', label: 'Monthly theme' },
  { levelId: 'LEVEL_TWO', labelKey: 'L2', label: 'Weekly theme' },
];

describe('PlanTreeBlock', () => {
  afterEach(() => jest.restoreAllMocks());

  it('shows any plan as a tree of its own levels and approves a node as an exact version', async () => {
    const nodes = [
      item({
        itemId: 'm',
        kind: 'PLAN_NODE',
        levelId: 'LEVEL_ONE',
        title: 'December theme',
        isSuggestion: false,
        state: 'PROPOSED',
        versionNo: 2,
      }),
      item({
        itemId: 'w',
        kind: 'PLAN_NODE',
        levelId: 'LEVEL_TWO',
        parentId: 'm',
        title: 'Week one',
        isSuggestion: false,
        state: 'DRAFT',
        isApproved: true,
        startDate: '2026-12-01',
      }),
    ];
    const calls = installOperationFetch([
      ['GET plan-tree', { levels, nodes }],
      ['POST items/m/approve', item({ itemId: 'm', isApproved: true })],
    ]);
    const onChanged = jest.fn();
    render(<PlanTreeBlock copy={copy} onChanged={onChanged} refreshKey={0} relationshipId={relationshipId} />);

    expect(await screen.findByText('Monthly theme → Weekly theme')).toBeInTheDocument();
    const [tree] = screen.getAllByRole('list');
    expect(within(tree).getByRole('button', { name: /December theme/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Week one/ })).toHaveTextContent('✔ approved · 2026-12-01');
    fireEvent.click(screen.getByRole('button', { name: /December theme/ }));
    fireEvent.click(await screen.findByRole('button', { name: copy.approve }));

    await waitFor(() =>
      expect(
        calls.some((call) => call.path === 'items/m/approve' && (call.body as { version: number }).version === 2)
      ).toBe(true)
    );
    expect(onChanged).toHaveBeenCalled();
  });

  it('says when there is no plan yet and retries a failed read', async () => {
    installOperationFetch([['GET plan-tree', refused(503, 'X', 'down')]]);
    const { unmount } = render(
      <PlanTreeBlock copy={copy} onChanged={jest.fn()} refreshKey={0} relationshipId={relationshipId} />
    );
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    installOperationFetch([['GET plan-tree', { levels, nodes: [] }]]);
    fireEvent.click(screen.getByRole('button', { name: copy.retry }));
    expect(await screen.findByText(copy.nothingYet)).toBeInTheDocument();
    unmount();
  });

  it('shows loading first', () => {
    installOperationFetch([['GET plan-tree', { levels, nodes: [] }]]);
    render(<PlanTreeBlock copy={copy} onChanged={jest.fn()} refreshKey={0} relationshipId={relationshipId} />);
    expect(screen.getByText(copy.loading)).toBeInTheDocument();
  });
});

describe('ProfileView', () => {
  afterEach(() => jest.restoreAllMocks());

  const labels = [
    item({
      itemId: 'l1',
      kind: 'PROFILE_LABEL',
      title: 'Dental clinic',
      state: 'INFERRED',
      reason: 'Found on a public page.',
    }),
    item({ itemId: 'l2', kind: 'PROFILE_LABEL', title: 'Pune', state: 'CONFIRMED', isSuggestion: false }),
  ];

  it('keeps what was inferred apart from what was confirmed and confirms a label in one tap', async () => {
    const calls = installOperationFetch([
      ['GET items?kind=PROFILE_LABEL', labels],
      [
        'GET items?kind=FINDING',
        [
          item({
            itemId: 'f1',
            kind: 'FINDING',
            title: 'Website',
            body: 'rao-dental.example',
            sourceRef: 'https://rao-dental.example',
            reason: 'Published openly.',
          }),
        ],
      ],
      ['POST labels/l1/confirm', item({ state: 'CONFIRMED' })],
      ['POST items/f1/hide', item({ state: 'HIDDEN' })],
    ]);
    const onChanged = jest.fn();
    render(<ProfileView copy={copy} onChanged={onChanged} refreshKey={0} relationshipId={relationshipId} />);

    expect(await screen.findByRole('list', { name: 'To confirm' })).toHaveTextContent('Dental clinic');
    expect(screen.getByRole('list', { name: 'Confirmed' })).toHaveTextContent('Pune');
    expect(screen.getAllByText(/rao-dental.example/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: copy.confirm }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(calls.find((call) => call.path === 'labels/l1/confirm')?.body).toEqual({ route: 'TOOL' });

    const finding = screen.getByRole('list', { name: 'Found on public pages' });
    fireEvent.click(within(finding).getByRole('button', { name: copy.hide }));
    await waitFor(() => expect(calls.some((call) => call.path === 'items/f1/hide')).toBe(true));
  });

  it('corrects a label and hides one', async () => {
    const calls = installOperationFetch([
      ['GET items?kind=PROFILE_LABEL', [labels[0]]],
      ['GET items?kind=FINDING', []],
      ['POST labels/l1/confirm', item({ state: 'CONFIRMED' })],
      ['POST items/l1/hide', item({ state: 'HIDDEN' })],
    ]);
    render(<ProfileView copy={copy} onChanged={jest.fn()} refreshKey={0} relationshipId={relationshipId} />);

    fireEvent.click(await screen.findByRole('button', { name: copy.correct }));
    fireEvent.change(screen.getByLabelText(copy.titleField), { target: { value: 'Dental surgery' } });
    fireEvent.click(screen.getByRole('button', { name: copy.save }));
    await waitFor(() =>
      expect(calls.find((call) => call.path === 'labels/l1/confirm')?.body).toEqual({
        correctedTitle: 'Dental surgery',
        route: 'TOOL',
      })
    );
    fireEvent.click(await screen.findByRole('button', { name: copy.hide }));
    await waitFor(() => expect(calls.some((call) => call.path === 'items/l1/hide')).toBe(true));
  });

  it('says plainly when a confirmation or removal was refused', async () => {
    installOperationFetch([
      ['GET items?kind=PROFILE_LABEL', [labels[0]]],
      ['GET items?kind=FINDING', []],
      [
        'POST labels/',
        refused(400, 'OPERATION_REQUEST_INVALID', 'The label must be plain words, up to 160 characters.'),
      ],
      ['POST items/', refused(404, 'OPERATION_ITEM_NOT_FOUND', 'That item was not found.')],
    ]);
    render(<ProfileView copy={copy} onChanged={jest.fn()} refreshKey={0} relationshipId={relationshipId} />);

    fireEvent.click(await screen.findByRole('button', { name: copy.confirm }));
    expect(await screen.findByText(/plain words/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.hide }));
    expect(await screen.findByText('That item was not found.')).toBeInTheDocument();
  });

  it('says when there is nothing yet and offers a retry when the read failed', async () => {
    installOperationFetch([
      ['GET items?kind=PROFILE_LABEL', []],
      ['GET items?kind=FINDING', []],
    ]);
    const { unmount } = render(
      <ProfileView copy={copy} onChanged={jest.fn()} refreshKey={0} relationshipId={relationshipId} />
    );
    expect(await screen.findByText(copy.nothingYet)).toBeInTheDocument();
    unmount();

    installOperationFetch([['GET items', refused(503, 'X', 'down')]]);
    render(<ProfileView copy={copy} onChanged={jest.fn()} refreshKey={0} relationshipId={relationshipId} />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    installOperationFetch([['GET items', []]]);
    fireEvent.click(screen.getByRole('button', { name: copy.retry }));
    expect(await screen.findByText(copy.nothingYet)).toBeInTheDocument();
  });
});

describe('PlatformsView', () => {
  afterEach(() => jest.restoreAllMocks());

  it('gives every platform an explicit answer and never asks for a password', async () => {
    const calls = installOperationFetch([['PUT platforms/', platforms()[0]]]);
    const onChanged = jest.fn();
    render(<PlatformsView copy={copy} onChanged={onChanged} platforms={platforms()} relationshipId={relationshipId} />);

    expect(screen.getByText(copy.noPasswords)).toBeInTheDocument();
    expect(screen.getByText('Not yet connectable')).toBeInTheDocument();
    expect(screen.getByText('Not answered yet')).toBeInTheDocument();
    expect(document.querySelector('input[type="password"]')).toBeNull();
    const website = screen.getByRole('group', { name: 'Website' });
    fireEvent.click(within(website).getByRole('button', { name: copy.answerAbsent }));

    await waitFor(() => expect(calls[0].body).toEqual({ answer: 'NOT_PRESENT', route: 'TOOL' }));
    expect(onChanged).toHaveBeenCalled();
    expect(calls[0].path).toBe('platforms/WEBSITE/answer');
  });

  it('starts consent on Facebook itself and shows the one platform that can be connected', async () => {
    const navigate = jest.fn();
    global.fetch = jest.fn(
      async () =>
        ({
          ok: true,
          status: 200,
          json: async () => ({ authorizationUrl: 'https://www.facebook.com/dialog', expiresAt: 'later' }),
        }) as unknown as Response
    ) as jest.Mock;
    render(
      <PlatformsView
        copy={copy}
        navigate={navigate}
        onChanged={jest.fn()}
        platforms={platforms()}
        relationshipId={relationshipId}
      />
    );

    expect(screen.getAllByRole('button', { name: copy.connect })).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: copy.connect }));

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('https://www.facebook.com/dialog'));
    expect(String((global.fetch as jest.Mock).mock.calls[0][0])).toBe('/api/provider-connections/meta/start');
  });

  it('tests and disconnects a connected platform and says when something failed', async () => {
    const connected = {
      ...platforms()[0],
      presence: 'CONNECTED_TESTED',
      connectionId: 'c1',
      accountName: 'Test page',
      canConnect: false,
    };
    const calls = installOperationFetch([['POST platforms/FACEBOOK/test', connected]]);
    const onChanged = jest.fn();
    const { rerender } = render(
      <PlatformsView copy={copy} onChanged={onChanged} platforms={[connected]} relationshipId={relationshipId} />
    );

    expect(screen.getByText('Connected and tested')).toBeInTheDocument();
    expect(screen.getByText(/Test page/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.test }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(calls[0].path).toBe('platforms/FACEBOOK/test');

    global.fetch = jest.fn(
      async () => ({ ok: true, status: 204, json: async () => ({}) }) as unknown as Response
    ) as jest.Mock;
    fireEvent.click(screen.getByRole('button', { name: copy.revoke }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(2));
    expect(String((global.fetch as jest.Mock).mock.calls[0][0])).toBe('/api/provider-connections/c1/revoke');

    global.fetch = jest.fn(
      async () => ({ ok: false, status: 503, json: async () => ({}) }) as unknown as Response
    ) as jest.Mock;
    fireEvent.click(screen.getByRole('button', { name: copy.revoke }));
    expect(await screen.findByText(/That did not work/)).toBeInTheDocument();
    rerender(
      <PlatformsView
        copy={copy}
        onChanged={onChanged}
        platforms={[{ ...connected, presence: 'NEEDS_REPAIR', canConnect: true }]}
        relationshipId={relationshipId}
      />
    );
    expect(screen.getByText('Needs to be reconnected')).toBeInTheDocument();
  });

  it('shows a refused answer and a refused test in plain words, and a failed connect start', async () => {
    installOperationFetch([
      ['PUT platforms/', refused(400, 'OPERATION_REQUEST_INVALID', 'Answer present, not present or public only.')],
      ['POST platforms/', refused(400, 'OPERATION_REQUEST_INVALID', 'That platform is not available.')],
    ]);
    const connected = { ...platforms()[0], presence: 'CONNECTED_TESTED', connectionId: null, canConnect: true };
    render(<PlatformsView copy={copy} onChanged={jest.fn()} platforms={[connected]} relationshipId={relationshipId} />);

    fireEvent.click(screen.getByRole('button', { name: copy.answerPresent }));
    expect(await screen.findByText(/Answer present/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.test }));
    expect(await screen.findByText('That platform is not available.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.revoke }));
    global.fetch = jest.fn(
      async () => ({ ok: false, status: 502, json: async () => ({}) }) as unknown as Response
    ) as jest.Mock;
    fireEvent.click(screen.getByRole('button', { name: copy.connect }));
    expect(await screen.findByText(/That did not work/)).toBeInTheDocument();
  });
});

describe('GoalsView', () => {
  afterEach(() => jest.restoreAllMocks());

  function renderGoals(
    skills: Parameters<typeof GoalsView>[0]['skills'] = [{ skillId: 'SKILL_ONE', state: 'NOT_SET' }],
    onChanged = jest.fn()
  ) {
    render(
      <GoalsView
        approvalModes={['CUSTOMER_APPROVAL', 'EXCEPTION_APPROVAL']}
        copy={copy}
        labels={{ SKILL_ONE: 'Profile' }}
        onChanged={onChanged}
        relationshipId={relationshipId}
        skills={skills}
      />
    );
    return onChanged;
  }

  it('sets a goal for a skill with every field the agent needs before it acts', async () => {
    const calls = installOperationFetch([['PUT goals/SKILL_ONE', item({ kind: 'GOAL' })]]);
    const onChanged = renderGoals();

    expect(screen.getByRole('form', { name: 'Profile' })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(copy.baseline), { target: { value: 'None yet' } });
    fireEvent.change(screen.getByLabelText(copy.target), { target: { value: '10 posts' } });
    fireEvent.change(screen.getByLabelText(copy.evidenceSource), { target: { value: 'Owner record' } });
    fireEvent.change(screen.getByLabelText(copy.cadence), { target: { value: 'WEEKLY' } });
    fireEvent.change(screen.getByLabelText(copy.authority), { target: { value: 'EXCEPTION_APPROVAL' } });
    fireEvent.click(screen.getByRole('button', { name: copy.saveGoal }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(calls[0].body).toEqual({
      baseline: 'None yet',
      target: '10 posts',
      evidenceSource: 'Owner record',
      cadence: 'WEEKLY',
      authorityState: 'EXCEPTION_APPROVAL',
      route: 'TOOL',
    });
  });

  it('shows what was set, names a skill from its id when no label is given and says why a goal was refused', async () => {
    installOperationFetch([
      [
        'PUT goals/',
        refused(400, 'OPERATION_REQUEST_INVALID', 'The target must be plain words, up to 160 characters.'),
      ],
    ]);
    renderGoals([
      {
        skillId: 'CONTENT_STRATEGY',
        state: 'CONFIRMED',
        goal: item({
          kind: 'GOAL',
          payload: {
            baseline: 'a',
            target: 'b',
            evidenceSource: 'c',
            cadence: 'DAILY',
            authorityState: 'EXCEPTION_APPROVAL',
          },
        }),
      } as never,
    ]);

    expect(screen.getByRole('form', { name: 'Content strategy' })).toBeInTheDocument();
    expect(screen.getByDisplayValue('b')).toBeInTheDocument();
    expect(screen.getByText(copy.confirmed)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.saveGoal }));
    expect(await screen.findByText(/plain words/)).toBeInTheDocument();
  });

  it('holds an agent revision as pending until the customer accepts or declines it', async () => {
    const calls = installOperationFetch([['POST goals/SKILL_ONE/decision', item({ kind: 'GOAL' })]]);
    const onChanged = renderGoals([
      {
        skillId: 'SKILL_ONE',
        state: 'PENDING_CONFIRMATION',
        goal: item({
          kind: 'GOAL',
          payload: {
            baseline: 'a',
            target: 'b',
            evidenceSource: 'c',
            cadence: 'DAILY',
            authorityState: 'CUSTOMER_APPROVAL',
            pending: { target: '20 posts' },
          },
        }),
      },
    ]);

    expect(screen.getByText(/A change is waiting for you: 20 posts/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.accept }));
    await waitFor(() => expect(calls[0].body).toEqual({ accept: true, route: 'TOOL' }));
    fireEvent.click(screen.getByRole('button', { name: copy.declineDigest }));
    await waitFor(() => expect(calls[1].body).toEqual({ accept: false, route: 'TOOL' }));
    expect(onChanged).toHaveBeenCalledTimes(2);
  });

  it('shows a refused decision', async () => {
    installOperationFetch([['POST goals/', refused(404, 'OPERATION_ITEM_NOT_FOUND', 'That goal was not found.')]]);
    renderGoals([{ skillId: 'SKILL_ONE', state: 'PROPOSED' }]);

    fireEvent.click(screen.getByRole('button', { name: copy.accept }));
    expect(await screen.findByText('That goal was not found.')).toBeInTheDocument();
  });
});
