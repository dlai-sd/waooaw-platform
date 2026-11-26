// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R003, R027, R036
// Constitutional basis: C-001, C-042, C-059, C-061, C-063

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { ToolDecl } from '@/lib/agent-operation';
import { operationMessages } from '@/lib/operation-i18n';
import { ModeRail, surfaceIdOf } from './ModeRail';
import { ToolForm } from './ToolForm';
import {
  frameFixture,
  installOperationFetch,
  item,
  layers,
  modes,
  platforms,
  refused,
  relationshipId,
} from './operation-test-data';

const copy = operationMessages('en');
const frame = frameFixture();

function renderRail(activeMode: 'INDUCT' | 'GOALS' | 'OPERATIONS' = 'GOALS', labels: Record<string, string> = {}) {
  const handlers = { onMode: jest.fn(), onSurface: jest.fn(), onTool: jest.fn() };
  render(
    <ModeRail
      activeMode={activeMode}
      activeSurface="kernel:calendar"
      copy={copy}
      labels={labels}
      modes={frame.modes}
      workbenchHref="/relationships/rel-1?surface=overview"
      {...handlers}
    />
  );
  return handlers;
}

describe('ModeRail', () => {
  it('has the three modes on a narrow rail and the chosen mode’s menus beside it, in the agent’s own words', () => {
    const { onMode } = renderRail();
    const rail = within(screen.getByRole('navigation', { name: copy.modesLabel }));

    expect(rail.getAllByRole('button').map((button) => button.textContent?.replace(/^\S\s/, ''))).toEqual([
      'Get to know me',
      'Set goals',
      'Run and improve',
    ]);
    expect(rail.getByRole('button', { name: /Set goals/ })).toHaveAttribute('aria-current', 'true');
    fireEvent.click(rail.getByRole('button', { name: /Run and improve/ }));
    expect(onMode).toHaveBeenCalledWith('OPERATIONS');
    const panel = screen.getByRole('complementary', { name: copy.modePanelLabel });
    expect(within(panel).getByRole('heading', { name: 'Set goals' })).toBeInTheDocument();
    expect(within(panel).getByText('0 of 5 goals set')).toBeInTheDocument();
  });

  it('lists entries in order, marks the current surface and opens a chosen one', () => {
    const { onSurface } = renderRail();
    const nav = within(screen.getByRole('navigation', { name: 'Set goals' }));

    expect(nav.getAllByRole('button').map((button) => button.textContent)).toEqual([
      'Goals by skill',
      'Calendar',
      'Plan',
    ]);
    expect(nav.getByRole('button', { name: 'Calendar' })).toHaveAttribute('aria-current', 'page');
    fireEvent.click(nav.getByRole('button', { name: 'Plan' }));
    expect(onSurface).toHaveBeenCalledWith(expect.objectContaining({ entryId: 'PLAN' }));
    expect(surfaceIdOf(modes()[1].entries[0])).toBe('kernel:goals');
    expect(surfaceIdOf({ ...modes()[1].entries[0], surface: { kind: 'DOMAIN_BLOCK', target: 'X' } })).toBe(
      'block:GOALS_LIST'
    );
  });

  it('groups tools in build order, shows a flyout only when its tool is chosen and runs a plain tool at once', () => {
    const { onTool } = renderRail();

    expect(screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)).toEqual([
      'Anchors',
      'Plan',
      'Content',
    ]);
    expect(screen.queryByRole('button', { name: 'Image' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Event' }));
    expect(onTool).toHaveBeenCalledWith(expect.objectContaining({ toolId: 'EVENT' }));

    const post = screen.getByRole('button', { name: 'Post' });
    fireEvent.click(post);
    expect(post).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(screen.getByRole('button', { name: 'Image' }));
    expect(onTool).toHaveBeenLastCalledWith(
      expect.objectContaining({ toolId: 'POST' }),
      expect.objectContaining({ optionId: 'IMAGE' })
    );
    expect(screen.queryByRole('button', { name: 'Image' })).not.toBeInTheDocument();
    fireEvent.click(post);
    fireEvent.click(post);
    expect(screen.queryByRole('button', { name: 'Image' })).not.toBeInTheDocument();
  });

  it('folds both levels away and brings them back', () => {
    renderRail();

    fireEvent.click(screen.getByRole('button', { name: copy.collapseRail }));
    expect(screen.queryByRole('navigation', { name: copy.modesLabel })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.collapsePanel }));
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.expandRail }));
    fireEvent.click(screen.getByRole('button', { name: copy.expandPanel }));
    expect(screen.getByRole('navigation', { name: copy.modesLabel })).toBeInTheDocument();
    expect(screen.getByRole('complementary')).toBeInTheDocument();
  });

  it('keeps every old workbench tool one link away in Operations and lets a table replace the agent’s labels', () => {
    renderRail('OPERATIONS', { MODE_OPERATIONS: 'चलाएँ और सुधारें' });

    expect(screen.getByRole('link', { name: copy.workbenchEntry })).toHaveAttribute(
      'href',
      '/relationships/rel-1?surface=overview'
    );
    expect(
      within(screen.getByRole('complementary')).getByRole('heading', { name: 'चलाएँ और सुधारें' })
    ).toBeInTheDocument();
  });

  it('shows the first mode when the active one is not declared and no workbench link outside Operations', () => {
    render(
      <ModeRail
        activeMode="OPERATIONS"
        activeSurface="x"
        copy={copy}
        labels={{}}
        modes={frame.modes.slice(0, 1)}
        onMode={jest.fn()}
        onSurface={jest.fn()}
        onTool={jest.fn()}
        workbenchHref="/w"
      />
    );
    expect(
      within(screen.getByRole('complementary')).getByRole('heading', { name: 'Get to know me' })
    ).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: copy.workbenchEntry })).not.toBeInTheDocument();
  });
});

const goalsMode = modes()[1];
const toolByCommand = (id: string) =>
  goalsMode.toolGroups.flatMap((group) => group.tools).find((tool) => tool.toolId === id) as ToolDecl;

function renderForm(toolId: string, option?: { optionId: string; labelKey: string; label: string }, overrides = {}) {
  const handlers = { onCreated: jest.fn(), onClose: jest.fn(), onSchedule: jest.fn() };
  render(
    <ToolForm
      copy={copy}
      layers={layers()}
      option={option}
      planLevels={frame.planLevels}
      platforms={platforms()}
      relationshipId={relationshipId}
      today="2026-12-15"
      tool={toolByCommand(toolId)}
      {...handlers}
      {...overrides}
    />
  );
  return handlers;
}

describe('ToolForm', () => {
  afterEach(() => jest.restoreAllMocks());

  it('adds an own event on a chosen layer through the same command the conversation uses', async () => {
    const calls = installOperationFetch([['POST items', item({ itemId: 'new' })]]);
    const { onCreated } = renderForm('EVENT');

    fireEvent.change(screen.getByLabelText(copy.titleField), { target: { value: 'Clinic anniversary' } });
    fireEvent.change(screen.getByLabelText(copy.dateField), { target: { value: '2026-12-20' } });
    fireEvent.change(screen.getByLabelText(copy.layersLabel), { target: { value: 'SEASON' } });
    fireEvent.click(screen.getByRole('button', { name: copy.save }));

    await waitFor(() => expect(onCreated).toHaveBeenCalled());
    expect(calls[0].body).toEqual({
      kind: 'EVENT',
      title: 'Clinic anniversary',
      layer: 'SEASON',
      startDate: '2026-12-20',
      route: 'TOOL',
    });
    expect(calls[0].headers['Idempotency-Key']).toBeTruthy();
  });

  it('adds a post for a platform with its package component and the chosen format in the title', async () => {
    const calls = installOperationFetch([['POST items', item()]]);
    renderForm('POST', { optionId: 'IMAGE', labelKey: 'OPTION_IMAGE', label: 'Image' });

    expect(screen.getByLabelText(copy.titleField)).toHaveValue('Image: ');
    fireEvent.change(screen.getByLabelText(copy.titleField), { target: { value: 'Image: Festival' } });
    fireEvent.change(screen.getByLabelText(copy.textField), { target: { value: 'Happy festival.' } });
    fireEvent.change(screen.getByLabelText(copy.platformsTitle), { target: { value: 'INSTAGRAM' } });
    fireEvent.click(screen.getByRole('button', { name: copy.save }));

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].body).toMatchObject({
      kind: 'CONTENT',
      body: 'Happy festival.',
      platformId: 'INSTAGRAM',
      componentId: 'POSTS',
      startDate: '2026-12-15',
    });
  });

  it('asks for the parent from the level above when it adds a deeper level of the plan, and none for the first', async () => {
    const calls = installOperationFetch([
      [
        'GET plan-tree',
        {
          levels: frame.planLevels,
          nodes: [item({ itemId: 'm', kind: 'PLAN_NODE', levelId: 'LEVEL_ONE', title: 'December theme' })],
        },
      ],
      ['POST items', item()],
    ]);
    const second = { ...toolByCommand('THEME'), planLevel: 'LEVEL_TWO', toolId: 'WEEK' };
    render(
      <ToolForm
        copy={copy}
        layers={layers()}
        onClose={jest.fn()}
        onCreated={jest.fn()}
        onSchedule={jest.fn()}
        planLevels={frame.planLevels}
        platforms={platforms()}
        relationshipId={relationshipId}
        today="2026-12-15"
        tool={second}
      />
    );

    const parent = await screen.findByRole('combobox', { name: /Monthly theme/ });
    await screen.findByRole('option', { name: 'December theme' });
    fireEvent.change(screen.getByLabelText(copy.titleField), { target: { value: 'Week one' } });
    fireEvent.change(parent, { target: { value: 'm' } });
    fireEvent.click(screen.getByRole('button', { name: copy.save }));

    await waitFor(() => expect(calls.some((call) => call.path === 'items')).toBe(true));
    expect(calls.find((call) => call.path === 'items')?.body).toMatchObject({
      kind: 'PLAN_NODE',
      levelId: 'LEVEL_TWO',
      parentId: 'm',
    });
  });

  it('adds a first-level plan node and a note without a parent or a date', async () => {
    const calls = installOperationFetch([['POST items', item()]]);
    const { unmount } = render(
      <ToolForm
        copy={copy}
        layers={layers()}
        onClose={jest.fn()}
        onCreated={jest.fn()}
        onSchedule={jest.fn()}
        planLevels={frame.planLevels}
        platforms={platforms()}
        relationshipId={relationshipId}
        today="2026-12-15"
        tool={toolByCommand('THEME')}
      />
    );
    expect(screen.queryByRole('combobox', { name: /Monthly theme/ })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(copy.titleField), { target: { value: 'December' } });
    fireEvent.click(screen.getByRole('button', { name: copy.save }));
    await waitFor(() => expect(calls[0].body).toMatchObject({ kind: 'PLAN_NODE', levelId: 'LEVEL_ONE' }));
    unmount();

    const note = { toolId: 'NOTE', labelKey: 'N', label: 'Note', icon: 'documents', command: 'ADD_NOTE' as const };
    render(
      <ToolForm
        copy={copy}
        layers={layers()}
        onClose={jest.fn()}
        onCreated={jest.fn()}
        onSchedule={jest.fn()}
        planLevels={frame.planLevels}
        platforms={platforms()}
        relationshipId={relationshipId}
        today="2026-12-15"
        tool={note}
      />
    );
    expect(screen.queryByLabelText(copy.dateField)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(copy.titleField), { target: { value: 'Ask about banners' } });
    fireEvent.click(screen.getByRole('button', { name: copy.save }));
    await waitFor(() => expect(calls).toHaveLength(2));
    expect(calls[1].body).toEqual({ kind: 'NOTE', title: 'Ask about banners', route: 'TOOL' });
  });

  it('sends a slot tool to scheduling, because only an approved post can be scheduled', () => {
    const slot = { toolId: 'SLOT', labelKey: 'S', label: 'Slot', icon: 'calendar', command: 'ADD_SLOT' as const };
    const onSchedule = jest.fn();
    const onClose = jest.fn();
    render(
      <ToolForm
        copy={copy}
        layers={layers()}
        onClose={onClose}
        onCreated={jest.fn()}
        onSchedule={onSchedule}
        planLevels={frame.planLevels}
        platforms={platforms()}
        relationshipId={relationshipId}
        today="2026-12-15"
        tool={slot}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: copy.schedule }));
    fireEvent.click(screen.getByRole('button', { name: copy.cancel }));
    expect(onSchedule).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('shows why an own item was refused and closes without changing anything', async () => {
    installOperationFetch([
      ['POST items', refused(400, 'OPERATION_REQUEST_INVALID', 'The title must be plain words, up to 160 characters.')],
    ]);
    const { onClose } = renderForm('PLACEHOLDER');

    fireEvent.change(screen.getByLabelText(copy.titleField), { target: { value: 'Something' } });
    fireEvent.click(screen.getByRole('button', { name: copy.save }));
    expect(await screen.findByText(/plain words/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.cancel }));
    expect(onClose).toHaveBeenCalled();
  });
});
