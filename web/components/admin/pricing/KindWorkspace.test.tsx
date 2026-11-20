// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { fakeResponse, versionFixture, versionId } from '@/lib/pricing-admin-test-data';
import { KindWorkspace } from './KindWorkspace';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const originalFetch = global.fetch;
const rateBody = {
  threadId: 'llm',
  provider: 'p',
  unit: 'token',
  rawCostPaise: 3,
  fxBufferPct: 1,
  opsOverheadPct: 1,
  riskPremiumPct: 1,
};

afterEach(() => {
  global.fetch = originalFetch;
});

test('an empty kind invites the first draft and offers no workflow', () => {
  render(<KindWorkspace isFounder={false} kind="RATE" versions={[]} />);

  expect(screen.getByText('No versions yet. Create the first draft below.')).toBeInTheDocument();
  expect(screen.getByRole('form', { name: 'Thread rate draft' })).toBeInTheDocument();
  expect(screen.queryByRole('region', { name: /Workflow/ })).toBeNull();
});

test('opening an effective version prefills a new draft and offers a blank start', () => {
  const effective = versionFixture({
    state: 'EFFECTIVE',
    seed: true,
    body: rateBody,
    effectiveFrom: '2026-11-01T00:00:00Z',
  });
  render(<KindWorkspace isFounder kind="RATE" versions={[effective]} />);

  expect(screen.getByRole('rowheader', { name: 'thread:llm (seed)' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Open thread:llm version 2' }));

  expect(screen.getByLabelText('Thread identifier')).toHaveValue('llm');
  expect(screen.getByRole('button', { name: 'Create draft' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Start a blank draft' }));
  expect(screen.getByLabelText('Thread identifier')).toHaveValue('');
  expect(screen.queryByRole('button', { name: 'Start a blank draft' })).toBeNull();
});

test('a saved draft joins the list, is selected and shows its workflow', async () => {
  const created = versionFixture({ versionNo: 1, body: rateBody });
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, created));
  render(<KindWorkspace isFounder={false} kind="RATE" versions={[]} />);

  for (const [label, value] of Object.entries({
    'Thread identifier': 'llm',
    Provider: 'p',
    'Billing unit': 'token',
    'Raw cost per unit (paise)': '3',
    'Currency buffer (%)': '1',
    'Operations overhead (%)': '1',
    'Risk premium (%)': '1',
  })) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  expect(await screen.findByRole('region', { name: 'Workflow for version 1' })).toBeInTheDocument();
  const table = within(screen.getByRole('table', { name: 'Thread rate versions' }));
  expect(table.getByText('DRAFT')).toBeInTheDocument();
  expect(screen.getByRole('form', { name: 'Thread rate draft' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Save draft' })).toBeInTheDocument();
});

test('a workflow change updates the row in place', async () => {
  const draft = versionFixture({ body: rateBody });
  const discarded = { ...draft, state: 'DISCARDED' };
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, discarded));
  render(<KindWorkspace isFounder kind="RATE" versions={[draft]} />);

  fireEvent.click(screen.getByRole('button', { name: 'Open thread:llm version 2' }));
  fireEvent.change(screen.getByLabelText('Reason for discarding'), { target: { value: 'wrong' } });
  fireEvent.click(screen.getByRole('button', { name: 'Discard' }));

  await waitFor(() =>
    expect(screen.getByRole('table', { name: 'Thread rate versions' })).toHaveTextContent('DISCARDED')
  );
  expect(screen.getAllByRole('row')).toHaveLength(2);
  expect(jest.mocked(global.fetch).mock.calls[0][0]).toBe(`/api/admin/pricing/drafts/${versionId}/discard`);
});
