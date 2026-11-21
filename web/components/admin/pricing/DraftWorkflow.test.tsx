// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { fakeResponse, simulationFixture, versionFixture, versionId } from '@/lib/pricing-admin-test-data';
import { DraftWorkflow } from './DraftWorkflow';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
});

function paths() {
  return jest.mocked(global.fetch).mock.calls.map(([url]) => String(url).replace('/api/admin/pricing/', ''));
}

test('simulate shows the result and reloads the version', async () => {
  const simulated = versionFixture({ state: 'SIMULATED' });
  global.fetch = jest
    .fn()
    .mockResolvedValueOnce(fakeResponse(200, { ...simulationFixture, warnings: [] }))
    .mockResolvedValueOnce(fakeResponse(200, simulated));
  const onChanged = jest.fn();
  const onSimulated = jest.fn();
  render(
    <DraftWorkflow isFounder={false} onChanged={onChanged} onSimulated={onSimulated} version={versionFixture()} />
  );

  fireEvent.click(screen.getByRole('button', { name: 'Simulate' }));

  expect(await screen.findByRole('region', { name: 'Simulation result' })).toBeInTheDocument();
  expect(onSimulated).toHaveBeenCalledWith(expect.objectContaining({ draftId: 'd1' }));
  await waitFor(() => expect(onChanged).toHaveBeenCalledWith(simulated));
  expect(paths()).toEqual([`drafts/${versionId}/simulate`, `drafts/${versionId}`]);
  expect(screen.getByRole('status')).toHaveTextContent('Simulation complete.');
});

test('a failed simulation shows the problem and does not reload', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(409, { code: 'PRICING_VERSION_CONFLICT' }));
  const onChanged = jest.fn();
  render(<DraftWorkflow isFounder onChanged={onChanged} version={versionFixture()} />);

  fireEvent.click(screen.getByRole('button', { name: 'Simulate' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('Reload it and try again');
  expect(onChanged).not.toHaveBeenCalled();
  expect(global.fetch).toHaveBeenCalledTimes(1);
});

test('submit is offered once simulated and a guarded change waits for confirmation', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, versionFixture({ state: 'SUBMITTED' })));
  const onChanged = jest.fn();
  render(
    <DraftWorkflow
      isFounder={false}
      onChanged={onChanged}
      version={versionFixture({ state: 'SIMULATED', needsSecondConfirmation: true })}
    />
  );

  const submit = screen.getByRole('button', { name: 'Submit for authorization' });
  expect(submit).toBeDisabled();
  fireEvent.click(screen.getByLabelText('I confirm this large change a second time'));
  fireEvent.click(submit);

  await waitFor(() => expect(onChanged).toHaveBeenCalledWith(expect.objectContaining({ state: 'SUBMITTED' })));
  expect(JSON.parse(String(jest.mocked(global.fetch).mock.calls[0][1]?.body))).toMatchObject({
    secondConfirmation: true,
  });
});

test('an unguarded submit needs no confirmation', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, versionFixture({ state: 'SUBMITTED' })));
  render(<DraftWorkflow isFounder={false} onChanged={jest.fn()} version={versionFixture({ state: 'SIMULATED' })} />);

  expect(screen.queryByLabelText('I confirm this large change a second time')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Submit for authorization' }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  expect(JSON.parse(String(jest.mocked(global.fetch).mock.calls[0][1]?.body)).secondConfirmation).toBe(false);
});

test('discard needs a reason and then discards', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, versionFixture({ state: 'DISCARDED' })));
  const onChanged = jest.fn();
  render(<DraftWorkflow isFounder onChanged={onChanged} version={versionFixture()} />);

  fireEvent.click(screen.getByRole('button', { name: 'Discard' }));
  expect(screen.getByRole('alert')).toHaveTextContent('Give a reason before discarding.');
  expect(global.fetch).not.toHaveBeenCalled();

  fireEvent.change(screen.getByLabelText('Reason for discarding'), { target: { value: ' wrong rate ' } });
  fireEvent.click(screen.getByRole('button', { name: 'Discard' }));

  await waitFor(() => expect(onChanged).toHaveBeenCalled());
  expect(JSON.parse(String(jest.mocked(global.fetch).mock.calls[0][1]?.body)).reason).toBe('wrong rate');
});

test('an administrator cannot authorize a submitted version and is told why', () => {
  render(<DraftWorkflow isFounder={false} onChanged={jest.fn()} version={versionFixture({ state: 'SUBMITTED' })} />);

  const authorize = screen.getByRole('button', { name: 'Authorize' });
  expect(authorize).toBeDisabled();
  expect(authorize).toHaveAccessibleDescription('Only the Founder can authorize.');
});

test('the Founder opens the dialog and focus returns to the button when it closes', async () => {
  render(<DraftWorkflow isFounder onChanged={jest.fn()} version={versionFixture({ state: 'SUBMITTED' })} />);

  const authorize = screen.getByRole('button', { name: 'Authorize' });
  fireEvent.click(authorize);
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Close' }));

  await waitFor(() => expect(authorize).toHaveFocus());
  expect(screen.queryByRole('dialog')).toBeNull();
});

test('authorizing inside the dialog reports the authorized version', async () => {
  const authorized = versionFixture({ state: 'AUTHORIZED' });
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, authorized));
  const onChanged = jest.fn();
  render(<DraftWorkflow isFounder onChanged={onChanged} version={versionFixture({ state: 'SUBMITTED' })} />);

  fireEvent.click(screen.getByRole('button', { name: 'Authorize' }));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Authorize' }));

  await waitFor(() => expect(onChanged).toHaveBeenCalledWith(authorized));
  expect(screen.queryByRole('dialog')).toBeNull();
});

test('only the Founder can activate an effective package for sale', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, { forSale: true }));
  const effective = versionFixture({ kind: 'PACKAGE', state: 'EFFECTIVE' });
  const { rerender } = render(<DraftWorkflow isFounder={false} onChanged={jest.fn()} version={effective} />);
  expect(screen.getByRole('button', { name: 'Activate for sale' })).toBeDisabled();
  expect(screen.getByText('Only the Founder can put a package on sale.')).toBeInTheDocument();

  const onChanged = jest.fn();
  rerender(<DraftWorkflow isFounder onChanged={onChanged} version={effective} />);
  fireEvent.click(screen.getByRole('button', { name: 'Activate for sale' }));

  await waitFor(() => expect(onChanged).toHaveBeenCalledWith(effective));
  expect(paths()).toEqual([`packages/${versionId}/activate-for-sale`]);
});

test('a settled version offers no workflow actions', () => {
  render(<DraftWorkflow isFounder onChanged={jest.fn()} version={versionFixture({ state: 'SUPERSEDED' })} />);
  expect(screen.queryByRole('button')).toBeNull();
});
