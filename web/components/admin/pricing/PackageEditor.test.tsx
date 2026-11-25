// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { fakeResponse, simulationFixture, versionFixture, versionId } from '@/lib/pricing-admin-test-data';
import type { PackageCatalogue, Simulation } from '@/lib/pricing-admin-types';
import { PackageEditor } from './PackageEditor';

const originalFetch = global.fetch;
const catalogue: PackageCatalogue = {
  agents: [{ agentType: 'dma', agentVersion: 'v3' }],
  threads: [{ threadId: 'llm', unit: 'token', rawCostPaise: 3 }],
};

afterEach(() => {
  global.fetch = originalFetch;
});

function type(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function fillPackage() {
  type('Agent type', 'dma');
  type('Agent version', 'v3');
  type('Package code', 'STARTER');
  type('Package name', 'Starter');
  type('Billing period (days)', '30');
  type('Price including GST (INR)', '2000');
  type('GST rate (%)', '18');
}

test('the running allocation sum says short, matches and over in words', () => {
  render(<PackageEditor catalogue={catalogue} draft={null} onSaved={jest.fn()} simulation={null} />);

  expect(screen.getByText(/Enter the package price to compare/)).toBeInTheDocument();
  fillPackage();
  expect(screen.getByText(/Derived base price INR 1,694.92 plus GST INR 305.08/)).toBeInTheDocument();
  expect(screen.getByText('Allocated INR 0.00 of INR 2,000.00: short by INR 2,000.00.')).toBeInTheDocument();

  type('Price allocation 1 (INR)', '2000');
  expect(screen.getByText('Allocated INR 2,000.00 of INR 2,000.00: matches the price.')).toBeInTheDocument();
  type('Price allocation 1 (INR)', '2500');
  expect(screen.getByText('Allocated INR 2,500.00 of INR 2,000.00: over by INR 500.00.')).toBeInTheDocument();
});

test('the agent selectors suggest the catalogue and the proactive row is present from the start', () => {
  const { container } = render(
    <PackageEditor catalogue={catalogue} draft={null} onSaved={jest.fn()} simulation={null} />
  );

  expect(container.querySelector('#package-agent-types option')).toHaveAttribute('value', 'dma');
  expect(container.querySelector('#package-agent-versions option')).toHaveAttribute('value', 'v3');
  expect(screen.getByRole('group', { name: /proactive messages \(fixed at 30\)/ })).toBeInTheDocument();
});

test('components can be added and removed and unavailable ones are flagged after simulation', () => {
  const simulation: Simulation = {
    ...simulationFixture,
    warnings: [
      { code: 'PACKAGE_COMPONENT_NOT_AVAILABLE', componentId: 'AD_BOOST', message: 'Ad boost is not available.' },
    ],
  };
  render(<PackageEditor catalogue={catalogue} draft={null} onSaved={jest.fn()} simulation={simulation} />);

  fireEvent.click(screen.getByRole('button', { name: 'Add component' }));
  type('Component identifier 2', 'AD_BOOST');
  expect(screen.getByText(/Not available: cannot go on sale/)).toBeInTheDocument();
  const rows = within(screen.getByRole('table', { name: 'Package components' })).getAllByRole('row');
  expect(rows[1]).toHaveTextContent('Available');
  expect(rows[1]).not.toHaveTextContent('Not available');
  expect(rows[2]).toHaveTextContent('Not available');

  fireEvent.click(screen.getByRole('button', { name: 'Remove component 2' }));
  expect(screen.queryByLabelText('Component identifier 2')).toBeNull();
});

test('only the selected component is edited at a time, and Add component selects the new one', () => {
  render(<PackageEditor catalogue={catalogue} draft={null} onSaved={jest.fn()} simulation={null} />);

  expect(screen.getByRole('table', { name: 'Package components' })).toBeInTheDocument();
  expect(screen.getByLabelText('Component identifier 1')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'Add component' }));
  expect(screen.getByLabelText('Component identifier 2')).toBeInTheDocument();
  expect(screen.queryByLabelText('Component identifier 1')).toBeNull();
  type('Component identifier 2', 'AD_BOOST');
  type('Quantity 2', '2');
  type('Price allocation 2 (INR)', '200');

  const table = screen.getByRole('table', { name: 'Package components' });
  expect(within(table).getAllByRole('row')[2]).toHaveTextContent('AD_BOOST');
  expect(within(table).getAllByRole('row')[2]).toHaveTextContent('INR 200.00');

  fireEvent.click(screen.getByRole('button', { name: 'Edit component 1' }));
  expect(screen.getByLabelText('Component identifier 1')).toBeInTheDocument();
  expect(screen.queryByLabelText('Component identifier 2')).toBeNull();
});

test('removing the selected component selects its neighbour', () => {
  render(<PackageEditor catalogue={catalogue} draft={null} onSaved={jest.fn()} simulation={null} />);

  fireEvent.click(screen.getByRole('button', { name: 'Add component' }));
  type('Component identifier 2', 'AD_BOOST');
  fireEvent.click(screen.getByRole('button', { name: 'Remove component 2' }));

  expect(screen.queryByLabelText('Component identifier 2')).toBeNull();
  expect(screen.getByLabelText('Component identifier 1')).toBeInTheDocument();
  expect(within(screen.getByRole('table', { name: 'Package components' })).getAllByRole('row')).toHaveLength(2);
});

test('problems are listed and nothing is sent until the package is complete', () => {
  global.fetch = jest.fn();
  render(<PackageEditor catalogue={catalogue} draft={null} onSaved={jest.fn()} simulation={null} />);

  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  expect(screen.getByRole('alert')).toHaveTextContent('The package needs attention');
  expect(screen.getByRole('list', { name: 'Package problems' })).toHaveTextContent('Agent type is required.');
  expect(global.fetch).not.toHaveBeenCalled();
});

test('a complete package is created with the owner subject key', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, versionFixture({ kind: 'PACKAGE' })));
  const onSaved = jest.fn();
  render(<PackageEditor catalogue={catalogue} draft={null} onSaved={onSaved} simulation={null} />);

  fillPackage();
  type('Price allocation 1 (INR)', '2000');
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
  render(<PackageEditor catalogue={catalogue} draft={draft} onSaved={jest.fn()} simulation={null} />);

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

test('an owner rejection keeps the form and names the violations', async () => {
  global.fetch = jest
    .fn()
    .mockResolvedValue(fakeResponse(422, { code: 'PRICING_BELOW_FLOOR', minimumCompliantPricePaise: 250000 }));
  render(<PackageEditor catalogue={catalogue} draft={null} onSaved={jest.fn()} simulation={null} />);

  fillPackage();
  type('Price allocation 1 (INR)', '2000');
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('Lowest compliant price: INR 2,500.00.');
});
