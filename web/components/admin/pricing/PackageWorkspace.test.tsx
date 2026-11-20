// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { fakeResponse, simulationFixture, versionFixture, versionId } from '@/lib/pricing-admin-test-data';
import { PackageWorkspace } from './PackageWorkspace';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));
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
});

test('creating a package moves the page to its own address and shows the workflow', async () => {
  const created = versionFixture({ kind: 'PACKAGE', body, subjectKey: 'package:dma|v3|STARTER' });
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, created));
  render(<PackageWorkspace catalogue={catalogue} isFounder={false} version={null} />);

  expect(screen.queryByRole('region', { name: /Workflow/ })).toBeNull();
  fireEvent.change(screen.getByLabelText('Agent type'), { target: { value: 'dma' } });
  fireEvent.change(screen.getByLabelText('Agent version'), { target: { value: 'v3' } });
  fireEvent.change(screen.getByLabelText('Package code'), { target: { value: 'STARTER' } });
  fireEvent.change(screen.getByLabelText('Package name'), { target: { value: 'Starter' } });
  fireEvent.change(screen.getByLabelText('Billing period (days)'), { target: { value: '30' } });
  fireEvent.change(screen.getByLabelText('Price including GST (INR)'), { target: { value: '2000' } });
  fireEvent.change(screen.getByLabelText('GST rate (%)'), { target: { value: '18' } });
  fireEvent.change(screen.getByLabelText('Price allocation 1 (INR)'), { target: { value: '2000' } });
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  await waitFor(() => expect(replace).toHaveBeenCalledWith(`/admin/pricing/packages/${versionId}`));
  expect(screen.getByRole('region', { name: 'Workflow for version 2' })).toBeInTheDocument();
});

test('an existing package does not navigate when saved and a simulation flags components in the editor', async () => {
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

  fireEvent.click(screen.getByRole('button', { name: 'Simulate' }));
  expect(await screen.findByText(/Not available: cannot go on sale/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
  expect(replace).not.toHaveBeenCalled();
});
