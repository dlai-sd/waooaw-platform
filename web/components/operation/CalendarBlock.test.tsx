// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R005, R006, R007
// Constitutional basis: C-001, C-023, C-059, C-061, C-063

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { operationMessages } from '@/lib/operation-i18n';
import { CalendarBlock, type CalendarViewName } from './CalendarBlock';
import { installOperationFetch, item, layers, platforms, refused, relationshipId } from './operation-test-data';

const copy = operationMessages('en');

function calendar(
  entries = [item()],
  limits: Array<{ componentId: string; label: string; remaining: number | null; committed: number; known: boolean }> = [
    { componentId: 'POSTS', label: 'Posts', remaining: 3, committed: 1, known: true },
  ]
) {
  return {
    from: '2026-12-01',
    to: '2026-12-31',
    entries,
    layers: layers(),
    limits,
    evidenceState: 'X',
    sourceFreshness: null,
  };
}

function renderBlock(view: CalendarViewName = 'MONTH', props: Partial<Parameters<typeof CalendarBlock>[0]> = {}) {
  const handlers = { onSelect: jest.fn(), onLoaded: jest.fn(), onChanged: jest.fn() };
  const utils = render(
    <CalendarBlock
      copy={copy}
      month={12}
      platforms={platforms()}
      refreshKey={0}
      relationshipId={relationshipId}
      selectedId={null}
      today="2026-12-15"
      view={view}
      year={2026}
      {...handlers}
      {...props}
    />
  );
  return { ...handlers, ...utils };
}

describe('CalendarBlock', () => {
  afterEach(() => jest.restoreAllMocks());

  it('shows the month as a table and as a list, the entries on their days, and the package limits', async () => {
    installOperationFetch([
      [
        'GET calendar',
        calendar([
          item(),
          item({
            itemId: 'n1',
            kind: 'NOTE',
            title: 'Customer note',
            startDate: '2026-12-02',
            isSuggestion: false,
            authorState: 'CUSTOMER_OWNED',
          }),
        ]),
      ],
    ]);
    const { onLoaded } = renderBlock();

    expect(screen.getByText(copy.loading)).toBeInTheDocument();
    expect((await screen.findAllByRole('button', { name: 'Harvest festival' })).length).toBe(2);
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getAllByRole('row').length).toBeGreaterThan(5);
    expect(screen.getByText(/Posts: 3 left/)).toBeInTheDocument();
    expect(screen.getByText(/1 scheduled/)).toBeInTheDocument();
    expect(onLoaded).toHaveBeenCalledWith(expect.objectContaining({ from: '2026-12-01' }));
    expect(document.querySelector('[aria-current="date"]')).toHaveTextContent('15');
  });

  it('opens the item card for a selected entry and reloads after a change', async () => {
    const calls = installOperationFetch([
      ['GET calendar', calendar()],
      ['POST items/i1/accept', item({ state: 'ACCEPTED', isSuggestion: false })],
    ]);
    const { onSelect, onChanged, onLoaded, rerender } = renderBlock();
    const entry = (await screen.findAllByRole('button', { name: 'Harvest festival' }))[0];
    fireEvent.click(entry);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ itemId: 'i1' }));

    rerender(
      <CalendarBlock
        copy={copy}
        month={12}
        onChanged={onChanged}
        onLoaded={onLoaded}
        onSelect={onSelect}
        platforms={platforms()}
        refreshKey={0}
        relationshipId={relationshipId}
        selectedId="i1"
        today="2026-12-15"
        view="MONTH"
        year={2026}
      />
    );
    fireEvent.click(await screen.findByRole('button', { name: copy.accept }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(onSelect).toHaveBeenLastCalledWith(expect.objectContaining({ state: 'ACCEPTED' }));
    expect(calls.some((call) => call.path === 'items/i1/accept')).toBe(true);
  });

  it('lets the customer switch layers on and off, warns about sensitive ones and adds their own', async () => {
    const calls = installOperationFetch([
      ['GET calendar', calendar()],
      ['PUT layers/SEASON', { layerId: 'SEASON', on: true }],
      [
        'POST layers',
        {
          layerId: 'CUSTOM_ABC',
          labelKey: 'LAYER_CUSTOM',
          label: 'Family dates',
          sensitive: false,
          on: true,
          custom: true,
        },
      ],
    ]);
    const { onChanged } = renderBlock();
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    expect(screen.getByLabelText(/Religion/)).not.toBeChecked();
    expect(screen.getByText(new RegExp(copy.sensitiveNote))).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Seasons/));
    await waitFor(() => expect(calls.some((call) => call.method === 'PUT' && call.body?.on === true)).toBe(true));
    fireEvent.change(screen.getByLabelText(copy.layerName), { target: { value: 'Family dates' } });
    fireEvent.click(screen.getByRole('button', { name: copy.addLayer }));

    await waitFor(() =>
      expect(calls.some((call) => call.path === 'layers' && call.body?.label === 'Family dates')).toBe(true)
    );
    expect(onChanged).toHaveBeenCalledTimes(2);
  });

  it('says why a layer change was refused', async () => {
    installOperationFetch([
      ['GET calendar', calendar()],
      ['PUT layers/', refused(400, 'OPERATION_LAYER_UNKNOWN', 'That layer is not available.')],
      [
        'POST layers',
        refused(409, 'OPERATION_PACKAGE_LIMIT_REACHED', 'You have reached the number of layers you can add.'),
      ],
    ]);
    renderBlock();
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    fireEvent.click(screen.getByLabelText(/Festivals/));
    expect(await screen.findByText('That layer is not available.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(copy.layerName), { target: { value: 'More' } });
    fireEvent.click(screen.getByRole('button', { name: copy.addLayer }));
    expect(await screen.findByText(/reached the number of layers/)).toBeInTheDocument();
  });

  it('shows only the week of today in the week view', async () => {
    installOperationFetch([['GET calendar', calendar()]]);
    renderBlock('WEEK');
    await screen.findAllByRole('button', { name: 'Harvest festival' });

    const rows = within(screen.getByRole('table')).getAllByRole('row');
    expect(rows).toHaveLength(2);
    expect(within(rows[1]).getByText('15')).toBeInTheDocument();
  });

  it('shows one lane per platform in the platforms view and the storyboard in date order', async () => {
    installOperationFetch([
      [
        'GET calendar',
        calendar([
          item({
            itemId: 'c1',
            kind: 'CONTENT',
            title: 'A post',
            platformId: 'FACEBOOK',
            startDate: '2026-12-05',
            isSuggestion: false,
          }),
          item({ itemId: 'p1', kind: 'PLAN_NODE', title: 'A story', startDate: '2026-12-01', isSuggestion: false }),
        ]),
      ],
    ]);
    const { unmount } = renderBlock('PLATFORMS');
    await screen.findAllByRole('button', { name: 'A post' });
    expect(
      within(screen.getByRole('region', { name: 'Facebook' })).getByRole('button', { name: 'A post' })
    ).toBeInTheDocument();
    expect(within(screen.getByRole('region', { name: 'Instagram' })).queryByRole('button')).not.toBeInTheDocument();
    unmount();

    renderBlock('STORYBOARD');
    await screen.findAllByRole('button', { name: 'A story' });
    const story = document.querySelector('.op-storyboard') as HTMLElement;
    expect(
      within(story)
        .getAllByRole('button')
        .map((button) => button.textContent)
    ).toEqual(['A story', 'A post']);
  });

  it('says when nothing is on the calendar and when a limit has not been read', async () => {
    installOperationFetch([
      [
        'GET calendar',
        calendar([], [{ componentId: 'POSTS', label: 'Posts', remaining: null, committed: 0, known: false }]),
      ],
    ]);
    renderBlock();

    expect(await screen.findByText(copy.nothingYet)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`Posts: ${copy.limitUnknown}`))).toBeInTheDocument();
    expect(screen.queryByText(/scheduled/)).not.toBeInTheDocument();
  });

  it('offers a retry when the calendar could not be read and changes nothing', async () => {
    const calls = installOperationFetch([['GET calendar', refused(503, 'OPERATION_UNAVAILABLE', 'down')]]);
    renderBlock();

    expect(await screen.findByRole('alert')).toHaveTextContent(copy.failed);
    installOperationFetch([['GET calendar', calendar()]]);
    fireEvent.click(screen.getByRole('button', { name: copy.retry }));
    expect((await screen.findAllByRole('button', { name: 'Harvest festival' })).length).toBeGreaterThan(0);
    expect(calls).toHaveLength(1);
  });

  it('shows a selected entry that is no longer in the month as nothing selected', async () => {
    installOperationFetch([['GET calendar', calendar()]]);
    renderBlock('MONTH', { selectedId: 'gone' });
    await screen.findAllByRole('button', { name: 'Harvest festival' });
    expect(screen.queryByRole('article')).not.toBeInTheDocument();
  });
});
