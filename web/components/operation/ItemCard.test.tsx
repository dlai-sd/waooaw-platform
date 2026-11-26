// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R007, R017, R030, R036
// Constitutional basis: C-001, C-023, C-059, C-063

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { operationMessages } from '@/lib/operation-i18n';
import { ItemCard } from './ItemCard';
import { installOperationFetch, item, refused, relationshipId } from './operation-test-data';

const copy = operationMessages('en');

function renderCard(overrides = {}, onChanged = jest.fn()) {
  render(<ItemCard copy={copy} item={item(overrides)} onChanged={onChanged} relationshipId={relationshipId} />);
  return onChanged;
}

describe('ItemCard', () => {
  afterEach(() => jest.restoreAllMocks());

  it('shows a suggestion as a suggestion with its reason, source and confidence, and accepts it as an accepted route', async () => {
    const calls = installOperationFetch([['POST items/i1/accept', item({ state: 'ACCEPTED', isSuggestion: false })]]);
    const onChanged = renderCard();

    expect(screen.getByText('Suggested by your agent')).toBeInTheDocument();
    expect(screen.getAllByText(copy.suggestion).length).toBeGreaterThan(0);
    expect(screen.getByText(/Fits the business\./)).toBeInTheDocument();
    expect(screen.getByText(/80%/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.accept }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(calls[0].body).toEqual({ route: 'ACCEPTED' });
    expect(calls[0].headers['Idempotency-Key']).toBeTruthy();
  });

  it('hands an item over, takes it back and offers undo only when there is something to undo', async () => {
    const calls = installOperationFetch([['POST items/i1/', item()]]);
    renderCard({ isSuggestion: false, authorState: 'CUSTOMER_EDITED', versionNo: 1 });
    expect(screen.queryByRole('button', { name: copy.undoItem })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.handOver }));
    await waitFor(() => expect(calls.map((call) => call.path)).toEqual(['items/i1/hand-over']));
  });

  it('takes back an item the customer owns and undoes the last change', async () => {
    const calls = installOperationFetch([['POST items/i1/', item()]]);
    renderCard({ isSuggestion: false, authorState: 'CUSTOMER_OWNED', versionNo: 3 });

    expect(screen.getByText(/Yours — your agent leaves it alone/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.takeBack }));
    await waitFor(() => expect(calls).toHaveLength(1));
    fireEvent.click(screen.getByRole('button', { name: copy.undoItem }));
    await waitFor(() => expect(calls.map((call) => call.path)).toEqual(['items/i1/take-back', 'items/i1/undo']));
  });

  it('hides and shows again', async () => {
    const calls = installOperationFetch([['POST items/i1/', item()]]);
    const { unmount } = render(
      <ItemCard
        copy={copy}
        item={item({ isSuggestion: false })}
        onChanged={jest.fn()}
        relationshipId={relationshipId}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: copy.hide }));
    await waitFor(() => expect(calls[0].path).toBe('items/i1/hide'));
    unmount();
    render(
      <ItemCard
        copy={copy}
        item={item({ isSuggestion: false, state: 'HIDDEN' })}
        onChanged={jest.fn()}
        relationshipId={relationshipId}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: copy.restore }));
    await waitFor(() => expect(calls[1].path).toBe('items/i1/restore'));
  });

  it('approves the exact version it shows and offers rejection until it is approved', async () => {
    const calls = installOperationFetch([['POST items/i1/', item()]]);
    renderCard({ kind: 'CONTENT', isSuggestion: false, state: 'PROPOSED', versionNo: 4, startDate: null });

    fireEvent.click(screen.getByRole('button', { name: copy.approve }));
    await waitFor(() => expect(calls[0].body).toEqual({ version: 4, route: 'TOOL' }));
    fireEvent.click(screen.getByRole('button', { name: copy.reject }));
    await waitFor(() => expect(calls[1].path).toBe('items/i1/reject'));
  });

  it('does not offer approval for a suggestion, an approved version or a plain event', () => {
    renderCard({ kind: 'CONTENT', isSuggestion: true, state: 'PROPOSED' });
    expect(screen.queryByRole('button', { name: copy.approve })).not.toBeInTheDocument();
  });

  it('does not offer approval once approved', () => {
    renderCard({
      kind: 'PLAN_NODE',
      isSuggestion: false,
      isApproved: true,
      authorState: 'APPROVED_VERSION',
      state: 'APPROVED',
    });
    expect(screen.queryByRole('button', { name: copy.approve })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: copy.reject })).not.toBeInTheDocument();
    expect(screen.getByText('Approved version')).toBeInTheDocument();
  });

  it('edits through the same command and keeps the version it was looking at', async () => {
    const calls = installOperationFetch([['PATCH items/i1', item({ title: 'Renamed', versionNo: 2 })]]);
    const onChanged = renderCard({ isSuggestion: false, versionNo: 2, body: 'Old text' });

    fireEvent.click(screen.getByRole('button', { name: copy.edit }));
    fireEvent.change(screen.getByLabelText(copy.titleField), { target: { value: 'Renamed' } });
    fireEvent.change(screen.getByLabelText(copy.textField), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: copy.save }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(calls[0].body).toMatchObject({
      title: 'Renamed',
      expectedVersion: 2,
      route: 'TOOL',
      startDate: '2026-12-10',
    });
    expect(calls[0].body).not.toHaveProperty('body');
  });

  it('cancels an edit', () => {
    renderCard({ isSuggestion: false });
    fireEvent.click(screen.getByRole('button', { name: copy.edit }));
    fireEvent.click(screen.getByRole('button', { name: copy.cancel }));
    expect(screen.getByRole('button', { name: copy.edit })).toBeInTheDocument();
  });

  it('moves to another day and only when the day actually changes', async () => {
    const calls = installOperationFetch([['POST items/i1/move', item({ startDate: '2026-12-20' })]]);
    renderCard({ isSuggestion: false });
    const move = screen.getByRole('button', { name: copy.move });
    expect(move).toBeDisabled();

    fireEvent.change(screen.getByLabelText(copy.moveTo), { target: { value: '2026-12-20' } });
    fireEvent.click(move);

    await waitFor(() => expect(calls[0].body).toEqual({ start: '2026-12-20', route: 'TOOL' }));
  });

  it('says in plain words why a change was refused and changes nothing', async () => {
    installOperationFetch([
      [
        'POST items/i1/accept',
        refused(409, 'OPERATION_CONFLICT', 'This changed while you were working. Reload and try again.'),
      ],
    ]);
    const onChanged = renderCard();

    fireEvent.click(screen.getByRole('button', { name: copy.accept }));

    expect(await screen.findByText(/changed while you were working/)).toBeInTheDocument();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it('shows no reason block for an item the customer made', () => {
    renderCard({ isSuggestion: false, reason: null, startDate: null, origin: 'CUSTOMER' });
    expect(screen.queryByText(new RegExp(`${copy.because}:`))).not.toBeInTheDocument();
  });

  it('shows the source and leaves out confidence when there is none', () => {
    renderCard({ confidence: null, sourceRef: null });
    expect(screen.queryByText(new RegExp(copy.confidence))).not.toBeInTheDocument();
    expect(screen.queryByText(new RegExp(copy.source))).not.toBeInTheDocument();
  });
});
