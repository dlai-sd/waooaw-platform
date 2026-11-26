// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { type ComponentProps, useState } from 'react';
import { fakeResponse, simulationFixture, versionFixture, versionId } from '@/lib/pricing-admin-test-data';
import type { PackageCatalogue, Simulation } from '@/lib/pricing-admin-types';
import { PackageEditor, type PackageTab } from './PackageEditor';

const originalFetch = global.fetch;
const catalogue: PackageCatalogue = {
  agents: [{ agentType: 'dma', agentVersion: 'v3' }],
  threads: [{ threadId: 'llm', unit: 'token', rawCostPaise: 3 }],
};

afterEach(() => {
  global.fetch = originalFetch;
});

// The tabs belong to the workspace; here small buttons stand in for them so one editor keeps its state across tabs.
function Editor(props: Partial<ComponentProps<typeof PackageEditor>>) {
  const [tab, setTab] = useState<PackageTab>('details');
  return (
    <>
      {(['details', 'components', 'review'] as const).map((id) => (
        <button key={id} onClick={() => setTab(id)} type="button">{`Go ${id}`}</button>
      ))}
      <PackageEditor catalogue={catalogue} draft={null} onSaved={jest.fn()} simulation={null} {...props} tab={tab} />
    </>
  );
}

const go = (tab: PackageTab) => fireEvent.click(screen.getByRole('button', { name: `Go ${tab}` }));

function type(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function fillPackage() {
  go('details');
  type('Agent type', 'dma');
  type('Agent version', 'v3');
  type('Package code', 'STARTER');
  type('Package name', 'Starter');
  type('Billing period (days)', '30');
  type('Price including GST (INR)', '2000');
  type('GST rate (%)', '18');
}

function allocate(component: number, value: string) {
  go('components');
  fireEvent.click(screen.getByRole('button', { name: `Edit component ${component}` }));
  type(`Price allocation ${component} (INR)`, value);
  fireEvent.click(screen.getByRole('button', { name: 'Back to components' }));
}

test('the running allocation sum says short, matches and over in words', () => {
  render(<Editor />);

  go('components');
  expect(screen.getByText(/Enter the package price to compare/)).toBeInTheDocument();
  fillPackage();
  expect(screen.getByText(/Derived base price INR 1,694.92 plus GST INR 305.08/)).toBeInTheDocument();
  go('components');
  expect(screen.getByText('Allocated INR 0.00 of INR 2,000.00: short by INR 2,000.00.')).toBeInTheDocument();

  allocate(1, '2000');
  expect(screen.getByText('Allocated INR 2,000.00 of INR 2,000.00: matches the price.')).toBeInTheDocument();
  allocate(1, '2500');
  expect(screen.getByText('Allocated INR 2,500.00 of INR 2,000.00: over by INR 500.00.')).toBeInTheDocument();
});

test('the agent selectors suggest the catalogue and the proactive row is present from the start', () => {
  const { container } = render(<Editor />);

  expect(container.querySelector('#package-agent-types option')).toHaveAttribute('value', 'dma');
  expect(container.querySelector('#package-agent-versions option')).toHaveAttribute('value', 'v3');
  go('components');
  fireEvent.click(screen.getByRole('button', { name: 'Edit component 1' }));
  expect(screen.getByRole('group', { name: /proactive messages \(fixed at 30\)/ })).toBeInTheDocument();
});

test('components can be added and removed and unavailable ones are flagged after simulation', () => {
  const simulation: Simulation = {
    ...simulationFixture,
    warnings: [
      { code: 'PACKAGE_COMPONENT_NOT_AVAILABLE', componentId: 'AD_BOOST', message: 'Ad boost is not available.' },
    ],
  };
  render(<Editor simulation={simulation} />);

  go('components');
  fireEvent.click(screen.getByRole('button', { name: 'Add component' }));
  type('Component identifier 2', 'AD_BOOST');
  expect(screen.getByText(/Not available: cannot go on sale/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Back to components' }));
  const rows = within(screen.getByRole('table', { name: 'Package components' })).getAllByRole('row');
  expect(rows[1]).toHaveTextContent('Available');
  expect(rows[1]).not.toHaveTextContent('Not available');
  expect(rows[2]).toHaveTextContent('Not available');

  fireEvent.click(screen.getByRole('button', { name: 'Edit component 2' }));
  fireEvent.click(screen.getByRole('button', { name: 'Remove component 2' }));
  expect(within(screen.getByRole('table', { name: 'Package components' })).getAllByRole('row')).toHaveLength(2);
});

test('a component is edited on a page of its own, with a way back to the list', () => {
  render(<Editor />);

  go('components');
  expect(screen.getByRole('table', { name: 'Package components' })).toBeInTheDocument();
  expect(screen.queryByLabelText('Component identifier 1')).toBeNull();

  fireEvent.click(screen.getByRole('button', { name: 'Add component' }));
  expect(screen.getByLabelText('Component identifier 2')).toBeInTheDocument();
  expect(screen.queryByRole('table', { name: 'Package components' })).toBeNull();
  type('Component identifier 2', 'AD_BOOST');
  type('Quantity 2', '2');
  type('Price allocation 2 (INR)', '200');
  fireEvent.click(screen.getByRole('button', { name: 'Components' }));

  const table = screen.getByRole('table', { name: 'Package components' });
  expect(within(table).getAllByRole('row')[2]).toHaveTextContent('AD_BOOST');
  expect(within(table).getAllByRole('row')[2]).toHaveTextContent('INR 200.00');
});

test('removing a component returns to the list', () => {
  render(<Editor />);

  go('components');
  fireEvent.click(screen.getByRole('button', { name: 'Add component' }));
  type('Component identifier 2', 'AD_BOOST');
  fireEvent.click(screen.getByRole('button', { name: 'Remove component 2' }));

  expect(screen.queryByLabelText('Component identifier 2')).toBeNull();
  expect(within(screen.getByRole('table', { name: 'Package components' })).getAllByRole('row')).toHaveLength(2);
});

test('the review tab lists what still stops the package going on sale, one next step at a time', () => {
  render(<Editor />);

  go('review');
  const list = within(screen.getByRole('region', { name: 'What stops this going on sale' }));
  expect(list.getByText(/Details are complete/)).toHaveTextContent('To do');
  expect(list.getByText(/Details are complete/)).toHaveTextContent('Fill the missing details');
  expect(list.getByText(/Authorized by the Founder/)).not.toHaveTextContent('Only the Founder authorizes');
  expect(list.getByText(/On sale/)).toHaveTextContent('To do');
});

test('problems are listed and nothing is sent until the package is complete', () => {
  global.fetch = jest.fn();
  render(<Editor />);

  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  expect(screen.getByRole('alert')).toHaveTextContent('The package needs attention');
  expect(screen.getByRole('list', { name: 'Package problems' })).toHaveTextContent('Agent type is required.');
  expect(global.fetch).not.toHaveBeenCalled();
});

test('a complete package is created with the owner subject key', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, versionFixture({ kind: 'PACKAGE' })));
  const onSaved = jest.fn();
  render(<Editor onSaved={onSaved} />);

  fillPackage();
  allocate(1, '2000');
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  await waitFor(() => expect(onSaved).toHaveBeenCalled());
  const body = JSON.parse(String(jest.mocked(global.fetch).mock.calls[0][1]?.body));
  expect(body).toMatchObject({ kind: 'PACKAGE', subjectKey: 'package:dma|v3|STARTER' });
  expect(body.body.components).toEqual([
    expect.objectContaining({ componentId: 'PROACTIVE_MESSAGE', quantity: 30, priceAllocationPaise: 200000 }),
  ]);
});

test('an existing draft is loaded and saved in place', async () => {
  const draft = versionFixture({
    kind: 'PACKAGE',
    subjectKey: 'package:dma|v3|STARTER',
    body: {
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
    },
  });
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, draft));
  render(<Editor draft={draft} />);

  expect(screen.getByLabelText('Package name')).toHaveValue('Starter');
  type('Package name', 'Starter plus');
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  const [url, init] = jest.mocked(global.fetch).mock.calls[0];
  expect(url).toBe(`/api/admin/pricing/drafts/${versionId}`);
  expect(JSON.parse(String(init?.body))).toMatchObject({
    expectedVersion: '2:DRAFT:abcdef0123456789',
    body: { displayName: 'Starter plus' },
  });
});

test('a new draft can start from the values of an existing version but is created as a new record', async () => {
  const source = versionFixture({
    kind: 'PACKAGE',
    state: 'EFFECTIVE',
    subjectKey: 'package:dma|v3|STARTER',
    body: {
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
    },
  });
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, versionFixture({ kind: 'PACKAGE', versionNo: 3 })));
  render(<Editor seed={source} />);

  expect(screen.getByLabelText('Package name')).toHaveValue('Starter');
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  const [url, init] = jest.mocked(global.fetch).mock.calls[0];
  expect(url).toBe('/api/admin/pricing/drafts');
  expect(JSON.parse(String(init?.body))).toMatchObject({ kind: 'PACKAGE', subjectKey: 'package:dma|v3|STARTER' });
});

test('an owner rejection keeps the form and names the violations', async () => {
  global.fetch = jest
    .fn()
    .mockResolvedValue(fakeResponse(422, { code: 'PRICING_BELOW_FLOOR', minimumCompliantPricePaise: 250000 }));
  render(<Editor />);

  fillPackage();
  allocate(1, '2000');
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('Lowest compliant price: INR 2,500.00.');
});
