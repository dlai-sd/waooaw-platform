// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fakeResponse, simulationFixture, versionFixture, versionId } from '@/lib/pricing-admin-test-data';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PackageWorkspace } from './PackageWorkspace';

const replace = jest.fn();
const push = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace, push }) }));
jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const originalFetch = global.fetch;
const catalogue = { agents: [], threads: [] };
const body = {
  agentType: 'dma',
  agentVersion: 'v3',
  packageCode: 'STARTER',
  displayName: 'Starter',
  billingPeriodDays: 30,
  priceInclGstPaise: 200000,
  gstRatePercent: 18,
  infrastructureSharePaise: 0,
  components: [
    {
      componentId: 'PROACTIVE_MESSAGE',
      kind: 'COUNTED',
      quantity: 30,
      cadence: 'SPREAD',
      priceAllocationPaise: 200000,
      recipe: [],
      topupAllowed: false,
    },
  ],
};

afterEach(() => {
  global.fetch = originalFetch;
  replace.mockClear();
  push.mockClear();
});

const openTab = (name: string) => fireEvent.click(screen.getByRole('tab', { name }));

test('creating a package moves the page to its own address and shows the workflow on the review tab', async () => {
  const created = versionFixture({ kind: 'PACKAGE', body, subjectKey: 'package:dma|v3|STARTER' });
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, created));
  render(<PackageWorkspace catalogue={catalogue} isFounder={false} version={null} />);

  expect(screen.getByRole('heading', { name: 'New package' })).toBeInTheDocument();
  expect(screen.queryByRole('region', { name: /Workflow/ })).toBeNull();
  fireEvent.change(screen.getByLabelText('Agent type'), { target: { value: 'dma' } });
  fireEvent.change(screen.getByLabelText('Agent version'), { target: { value: 'v3' } });
  fireEvent.change(screen.getByLabelText('Package code'), { target: { value: 'STARTER' } });
  fireEvent.change(screen.getByLabelText('Package name'), { target: { value: 'Starter' } });
  fireEvent.change(screen.getByLabelText('Billing period (days)'), { target: { value: '30' } });
  fireEvent.change(screen.getByLabelText('Price including GST (INR)'), { target: { value: '2000' } });
  fireEvent.change(screen.getByLabelText('GST rate (%)'), { target: { value: '18' } });
  openTab('Components');
  fireEvent.click(screen.getByRole('button', { name: 'Edit component 1' }));
  fireEvent.change(screen.getByLabelText('Price allocation 1 (INR)'), { target: { value: '2000' } });
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  await waitFor(() => expect(replace).toHaveBeenCalledWith(`/admin/pricing/packages/${versionId}`));
  openTab('Review and sale');
  expect(screen.getByRole('region', { name: 'Workflow for version 2' })).toBeInTheDocument();
});

test('an authorized package is read as a record with a way to start a new version from it', () => {
  const authorized = versionFixture({ kind: 'PACKAGE', body, state: 'AUTHORIZED' });
  render(<PackageWorkspace catalogue={catalogue} isFounder version={authorized} />);

  expect(screen.getByRole('list', { name: 'Progress' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'New version from this' }));
  expect(push).toHaveBeenCalledWith(`/admin/pricing/packages/new?from=${versionId}`);
});

test('an existing package does not navigate when saved and a simulation flags the package on the review tab', async () => {
  const draft = versionFixture({ kind: 'PACKAGE', body });
  const simulation = {
    ...simulationFixture,
    warnings: [{ code: 'PACKAGE_COMPONENT_NOT_AVAILABLE', componentId: 'PROACTIVE_MESSAGE', message: 'Not released.' }],
  };
  global.fetch = jest
    .fn()
    .mockResolvedValueOnce(fakeResponse(200, simulation))
    .mockResolvedValueOnce(fakeResponse(200, { ...draft, state: 'SIMULATED' }))
    .mockResolvedValueOnce(fakeResponse(200, { ...draft, state: 'SIMULATED' }));
  render(<PackageWorkspace catalogue={catalogue} isFounder version={draft} />);

  openTab('Review and sale');
  fireEvent.click(screen.getByRole('button', { name: 'Simulate' }));
  expect(await screen.findByText(/Not available yet: PROACTIVE_MESSAGE/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
  expect(replace).not.toHaveBeenCalled();
});

test('saving a draft clears an older build-up so it never describes numbers the saved draft no longer has', async () => {
  const draft = versionFixture({ kind: 'PACKAGE', body });
  const simulation = {
    ...simulationFixture,
    buildUp: {
      costLines: [],
      infrastructureSharePaise: 0,
      costFloorPaise: 0,
      unauthorizedThreadIds: [],
      uncostedComponentIds: [],
      suggestionStatus: 'UNUSABLE' as const,
    },
  };
  global.fetch = jest
    .fn()
    .mockResolvedValueOnce(fakeResponse(200, simulation))
    .mockResolvedValueOnce(fakeResponse(200, { ...draft, state: 'SIMULATED' }))
    .mockResolvedValueOnce(fakeResponse(200, { ...draft, state: 'SIMULATED' }));
  render(<PackageWorkspace catalogue={catalogue} isFounder version={draft} />);

  openTab('Review and sale');
  fireEvent.click(screen.getByRole('button', { name: 'Simulate' }));
  expect(await screen.findByRole('table', { name: 'Cost lines' })).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
  await waitFor(() => expect(screen.queryByRole('table', { name: 'Cost lines' })).toBeNull());
  expect(screen.getByText(/Save the draft, then press Simulate/)).toBeInTheDocument();
});

test('the description and target margin are saved with the package', async () => {
  const draft = versionFixture({ kind: 'PACKAGE', body });
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, draft));
  render(<PackageWorkspace catalogue={catalogue} isFounder version={draft} />);

  fireEvent.change(screen.getByLabelText(/Description \(the customer maturity/), {
    target: { value: 'New to digital marketing.' },
  });
  fireEvent.change(screen.getByLabelText('Target margin for this package (%)'), { target: { value: '40' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
  const sent = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body as string);
  expect(sent.body.description).toBe('New to digital marketing.');
  expect(sent.body.targetMarginPct).toBe(40);
});
