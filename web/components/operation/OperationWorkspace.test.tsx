// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R003, R005, R027, R028, R029, R030, R031
// Constitutional basis: C-001, C-023, C-042, C-059, C-063

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { operationMessages } from '@/lib/operation-i18n';
import { OperationWorkspace } from './OperationWorkspace';
import { frameFixture, installOperationFetch, item, layers, refused, relationshipId } from './operation-test-data';

const copy = operationMessages('en');

const calendarBody = (entries = [item()]) => ({
  from: '2026-12-01',
  to: '2026-12-31',
  entries,
  layers: layers(),
  limits: [{ componentId: 'POSTS', label: 'Posts', remaining: 3, committed: 1, known: true }],
  evidenceState: 'X',
  sourceFreshness: null,
});

function baseRoutes(extra: [string, unknown][] = [], frame = frameFixture()): [string, unknown][] {
  return [
    ...extra,
    ['PUT mode', { ok: true }],
    ['POST tour-seen', { ok: true }],
    ['GET frame', frame],
    ['GET calendar', calendarBody()],
    ['GET items', []],
    ['GET plan-tree', { levels: frame.planLevels, nodes: [] }],
  ];
}

function renderWorkspace(props: Partial<Parameters<typeof OperationWorkspace>[0]> = {}) {
  return render(
    <OperationWorkspace
      copy={copy}
      initialFrame={frameFixture()}
      relationshipId={relationshipId}
      today="2026-12-15"
      workbenchHref="/relationships/rel-1?surface=overview"
      {...props}
    />
  );
}

describe('OperationWorkspace', () => {
  beforeEach(() => window.sessionStorage.clear());
  afterEach(() => jest.restoreAllMocks());

  it('opens on the calendar with the first unfinished mode, its menu, the readiness line and the guide beside it', async () => {
    installOperationFetch(baseRoutes());
    renderWorkspace();

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: copy.title })).toBeInTheDocument();
    expect((await screen.findAllByRole('button', { name: 'Harvest festival' })).length).toBeGreaterThan(0);
    expect(
      within(screen.getByRole('complementary', { name: copy.modePanelLabel })).getByRole('heading', {
        name: 'Get to know me',
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText('3 of 17 items confirmed', { selector: '.op-readiness-line, .op-readiness-line *' })
    ).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: copy.conversationLabel })).toHaveTextContent(
      'Confirm what I understood about your business.'
    );
    expect(screen.getByText('December 2026')).toBeInTheDocument();
    expect(screen.getByText(/Posts: 3 left/, { selector: '.op-meter' })).toBeInTheDocument();
    expect(screen.getByText(copy.statusNothingSelected)).toBeInTheDocument();
  });

  it('opens the shell’s docked conversation once, so the agent is beside the customer from the start', async () => {
    installOperationFetch(baseRoutes());
    const open = jest.fn();
    window.addEventListener('waooaw:open-conversation', open);
    const { unmount } = renderWorkspace();
    await screen.findAllByRole('button', { name: 'Harvest festival' });
    unmount();
    renderWorkspace();

    expect(open).toHaveBeenCalledTimes(1);
    window.removeEventListener('waooaw:open-conversation', open);
  });

  it('lets the customer hop to any mode at any time and remembers it', async () => {
    const calls = installOperationFetch(baseRoutes());
    renderWorkspace();
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    fireEvent.click(
      within(screen.getByRole('navigation', { name: copy.modesLabel })).getByRole('button', { name: /Run and improve/ })
    );

    expect(
      within(screen.getByRole('complementary', { name: copy.modePanelLabel })).getByRole('heading', {
        name: 'Run and improve',
      })
    ).toBeInTheDocument();
    await waitFor(() => expect(calls.some((call) => call.method === 'PUT' && call.path === 'mode')).toBe(true));
    expect(calls.find((call) => call.path === 'mode')?.body).toEqual({
      modeId: 'OPERATIONS',
      surface: 'kernel:calendar',
    });
  });

  it('takes the customer to the surface the next step names, through the same button in the line and in the guide', async () => {
    installOperationFetch(
      baseRoutes([
        ['GET items?kind=PROFILE_LABEL', [item({ kind: 'PROFILE_LABEL', title: 'Dental clinic', state: 'INFERRED' })]],
        ['GET items?kind=FINDING', []],
      ])
    );
    renderWorkspace();
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    fireEvent.click(
      within(document.querySelector('.op-readiness-line') as HTMLElement).getByRole('button', {
        name: 'Confirm profile',
      })
    );

    expect(await screen.findByRole('region', { name: copy.profileTitle })).toBeInTheDocument();
    expect(screen.getByText('Dental clinic')).toBeInTheDocument();
  });

  it('opens each kind of surface a declared entry points at', async () => {
    installOperationFetch(
      baseRoutes([
        ['GET items?kind=PROFILE_LABEL', []],
        ['GET items?kind=FINDING', []],
        ['GET items?kind=CONTENT', []],
        ['GET items?kind=SLOT', []],
        ['GET items?kind=DIGEST', []],
        ['GET items?kind=PLAN_NODE', []],
      ])
    );
    renderWorkspace({ initialMode: 'GOALS' });
    await screen.findAllByRole('button', { name: 'Harvest festival' });
    const panel = () => within(screen.getByRole('complementary', { name: copy.modePanelLabel }));

    fireEvent.click(panel().getByRole('button', { name: 'Goals by skill' }));
    expect(await screen.findByRole('region', { name: copy.goalsTitle })).toBeInTheDocument();
    fireEvent.click(panel().getByRole('button', { name: 'Plan' }));
    expect(await screen.findByRole('heading', { level: 2, name: copy.planTitle })).toBeInTheDocument();
    fireEvent.click(panel().getByRole('button', { name: 'Calendar' }));
    expect(await screen.findByRole('region', { name: copy.viewMonth })).toBeInTheDocument();

    fireEvent.click(
      within(screen.getByRole('navigation', { name: copy.modesLabel })).getByRole('button', { name: /Get to know me/ })
    );
    fireEvent.click(panel().getByRole('button', { name: 'Platforms' }));
    expect(await screen.findByRole('region', { name: copy.platformsTitle })).toBeInTheDocument();

    fireEvent.click(
      within(screen.getByRole('navigation', { name: copy.modesLabel })).getByRole('button', { name: /Run and improve/ })
    );
    for (const [entry, region] of [
      ['Approvals', copy.approvalsTitle],
      ['Published', copy.publishedTitle],
      ['Results', copy.resultsTitle],
      ['Improve', copy.improveTitle],
    ]) {
      fireEvent.click(panel().getByRole('button', { name: entry }));
      expect(await screen.findByRole('region', { name: region })).toBeInTheDocument();
    }
  });

  it('keeps old workbench links one click away and points a declared block entry at the workbench', async () => {
    installOperationFetch(baseRoutes());
    const block = {
      entryId: 'MATURITY',
      labelKey: 'NAV_MATURITY',
      label: 'Maturity report',
      icon: 'insights',
      order: 60,
      surface: { kind: 'DOMAIN_BLOCK', target: 'SUMMARY' },
      availabilityGate: 'ALWAYS',
    };
    const frame = frameFixture();
    frame.modes[0].mode.entries.push(block);
    renderWorkspace({ initialFrame: frame, initialMode: 'INDUCT' });
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    fireEvent.click(
      within(screen.getByRole('complementary', { name: copy.modePanelLabel })).getByRole('button', {
        name: 'Maturity report',
      })
    );

    expect(screen.getByRole('link', { name: /Maturity report/ })).toHaveAttribute(
      'href',
      '/relationships/rel-1?surface=entry-maturity'
    );
  });

  it('moves between months and back to today, and between the four views of one plan', async () => {
    installOperationFetch(baseRoutes());
    renderWorkspace();
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    fireEvent.click(screen.getByRole('button', { name: copy.nextMonth }));
    expect(screen.getByText('January 2027')).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: 'Harvest festival' })).not.toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: copy.previousMonth }));
    fireEvent.click(screen.getByRole('button', { name: copy.previousMonth }));
    expect(screen.getByText('November 2026')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.today }));
    expect(screen.getByText('December 2026')).toBeInTheDocument();

    const views = within(screen.getByRole('group', { name: copy.viewsLabel }));
    expect(
      views
        .getAllByRole('button')
        .map((button) => button.textContent)
        .slice(0, 5)
    ).toEqual([copy.viewMonth, copy.viewWeek, copy.viewPlatforms, copy.viewStoryboard, 'Confirm profile']);
    fireEvent.click(views.getByRole('button', { name: copy.viewWeek }));
    expect(views.getByRole('button', { name: copy.viewWeek })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(views.getByRole('button', { name: copy.viewStoryboard }));
    expect(await screen.findByRole('region', { name: copy.viewMonth })).toBeInTheDocument();
  });

  it('adds the customer’s own item from a tool, selects it and refreshes', async () => {
    const calls = installOperationFetch(
      baseRoutes([['POST items', item({ itemId: 'own', title: 'Clinic anniversary', isSuggestion: false })]])
    );
    renderWorkspace({ initialMode: 'GOALS' });
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    fireEvent.click(screen.getByRole('button', { name: 'Event' }));
    fireEvent.change(screen.getByLabelText(copy.titleField), { target: { value: 'Clinic anniversary' } });
    fireEvent.click(screen.getByRole('button', { name: copy.save }));

    await waitFor(() => expect(screen.getByText('Clinic anniversary', { selector: 'span' })).toBeInTheDocument());
    expect(calls.some((call) => call.method === 'POST' && call.path === 'items')).toBe(true);
    expect(calls.filter((call) => call.path === 'frame').length).toBeGreaterThan(0);
  });

  it('sends a slot tool to the approvals screen and closes a tool form', async () => {
    installOperationFetch(
      baseRoutes([
        ['GET items?kind=CONTENT', []],
        ['GET items?kind=PLAN_NODE', []],
        ['GET items?kind=SLOT', []],
      ])
    );
    const frame = frameFixture();
    frame.modes[1].mode.toolGroups[0].tools.push({
      toolId: 'SLOT',
      labelKey: 'S',
      label: 'Slot',
      icon: 'calendar',
      command: 'ADD_SLOT',
    });
    renderWorkspace({ initialFrame: frame, initialMode: 'GOALS' });
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    fireEvent.click(screen.getByRole('button', { name: 'Slot' }));
    fireEvent.click(screen.getByRole('button', { name: copy.schedule }));

    expect(await screen.findByRole('region', { name: copy.approvalsTitle })).toBeInTheDocument();
    expect(screen.queryByRole('form', { name: 'Slot' })).not.toBeInTheDocument();
  });

  it('undoes the last change to the selected item and redoes it by undoing the undo', async () => {
    const calls = installOperationFetch([
      ['GET calendar', calendarBody([item({ versionNo: 3, isSuggestion: false })])],
      ['POST items/i1/undo', item({ versionNo: 4, isSuggestion: false })],
      ...baseRoutes(),
    ]);
    renderWorkspace();
    const entry = (await screen.findAllByRole('button', { name: 'Harvest festival' }))[0];
    const undo = screen.getByRole('button', { name: new RegExp(`^↶ ${copy.undo}$`) });
    const redo = screen.getByRole('button', { name: new RegExp(`^↷ ${copy.redo}$`) });
    expect(undo).toBeDisabled();
    expect(redo).toBeDisabled();

    fireEvent.click(entry);
    await waitFor(() => expect(undo).toBeEnabled());
    fireEvent.click(undo);
    await waitFor(() => expect(redo).toBeEnabled());
    fireEvent.click(redo);
    await waitFor(() => expect(redo).toBeDisabled());
    expect(calls.filter((call) => call.path === 'items/i1/undo')).toHaveLength(2);
  });

  it('shows a refused undo in plain words', async () => {
    installOperationFetch([
      ['GET calendar', calendarBody([item({ versionNo: 3, isSuggestion: false })])],
      ['POST items/i1/undo', refused(400, 'OPERATION_REQUEST_INVALID', 'There is nothing to undo.')],
      ...baseRoutes(),
    ]);
    renderWorkspace();
    const undo = screen.getByRole('button', { name: new RegExp(`^↶ ${copy.undo}$`) });
    fireEvent.click((await screen.findAllByRole('button', { name: 'Harvest festival' }))[0]);
    await waitFor(() => expect(undo).toBeEnabled());

    fireEvent.click(undo);

    expect(await screen.findByText('There is nothing to undo.')).toBeInTheDocument();
  });

  it('gives a short tour once, skippable and replayable', async () => {
    const calls = installOperationFetch(baseRoutes());
    renderWorkspace({ initialFrame: frameFixture({ tourSeen: false }) });
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    expect(screen.getByRole('dialog', { name: copy.tourTitle })).toHaveTextContent(copy.tourBody);
    fireEvent.click(screen.getByRole('button', { name: copy.tourDone }));
    await waitFor(() => expect(calls.some((call) => call.path === 'tour-seen')).toBe(true));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.tourReplay }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: new RegExp(copy.help) }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('opens straight at a remembered mode and surface and names a stopped relationship', async () => {
    installOperationFetch(baseRoutes([['GET items', []]]));
    renderWorkspace({ initialFrame: frameFixture({ lastMode: 'GOALS', lastSurface: 'kernel:goals', stopped: true }) });

    expect(await screen.findByRole('region', { name: copy.goalsTitle })).toBeInTheDocument();
    expect(
      within(screen.getByRole('complementary', { name: copy.modePanelLabel })).getByRole('heading', {
        name: 'Set goals',
      })
    ).toBeInTheDocument();
    expect(screen.getAllByRole('alert').some((alert) => alert.textContent === copy.stoppedBanner)).toBe(true);
  });

  it('counts "Do it for me" in the guide and keeps the allowance up to date', async () => {
    installOperationFetch(
      baseRoutes([
        ['POST conversation/chats', { allowed: 1000, used: 11, remaining: 989, reached: false }],
        ['GET items', []],
      ])
    );
    renderWorkspace();
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    fireEvent.click(screen.getByRole('button', { name: copy.doItForMe }));

    expect(await screen.findByText('989')).toBeInTheDocument();
  });

  it('opens the conversation when the next step is to talk', async () => {
    installOperationFetch(baseRoutes());
    const frame = frameFixture();
    frame.modes[0].readiness.next = {
      modeId: 'INDUCT',
      textKey: 'K',
      text: 'Tell me about your business.',
      primaryLabel: 'Start',
      command: 'OPEN_CONVERSATION',
    };
    const open = jest.fn();
    window.sessionStorage.setItem(`waooaw:op-dock:${relationshipId}`, '1');
    window.addEventListener('waooaw:open-conversation', open);
    renderWorkspace({ initialFrame: frame });
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    fireEvent.click(
      within(document.querySelector('.op-readiness-line') as HTMLElement).getByRole('button', { name: 'Start' })
    );

    expect(open).toHaveBeenCalledTimes(1);
    window.removeEventListener('waooaw:open-conversation', open);
  });

  it('shows nothing to do when every mode is in order and picks Operations first', async () => {
    installOperationFetch(baseRoutes());
    const frame = frameFixture();
    for (const entry of frame.modes) {
      entry.readiness.state = 'READY';
      entry.readiness.next = null;
    }
    frame.next = null;
    renderWorkspace({ initialFrame: frame });

    expect(
      within(screen.getByRole('complementary', { name: copy.modePanelLabel })).getByRole('heading', {
        name: 'Run and improve',
      })
    ).toBeInTheDocument();
    expect(screen.getByText(copy.allDone)).toBeInTheDocument();
    await screen.findAllByRole('button', { name: 'Harvest festival' });
  });

  it('uses an agent without declared views or limits without breaking', async () => {
    installOperationFetch([['GET calendar', { ...calendarBody(), limits: [] }], ...baseRoutes()]);
    renderWorkspace({ initialFrame: frameFixture({ views: [] }) });
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    expect(screen.queryByText(/Posts:/, { selector: '.op-meter' })).not.toBeInTheDocument();
  });
});
