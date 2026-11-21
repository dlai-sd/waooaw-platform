// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { render, screen, within } from '@testing-library/react';
import { simulationFixture } from '@/lib/pricing-admin-test-data';
import { SimulatorPanel } from './SimulatorPanel';
import { VersionDiff } from './VersionDiff';

test('the simulator shows floor, margin, profiles, warnings, affected packages and the diff', () => {
  render(<SimulatorPanel result={simulationFixture} />);

  expect(screen.getByText('Cost floor').nextElementSibling).toHaveTextContent('INR 800.00');
  expect(screen.getByText('52.8%')).toBeInTheDocument();
  expect(screen.getByText('INR 1,500.00')).toBeInTheDocument();
  const profiles = within(screen.getByRole('table', { name: 'Usage profiles' }));
  expect(profiles.getByRole('rowheader', { name: 'TYPICAL' })).toBeInTheDocument();
  expect(profiles.getByRole('rowheader', { name: 'Busy salon' })).toBeInTheDocument();
  expect(screen.getByText('Price changes by more than 30 percent.')).toBeInTheDocument();
  const affected = within(screen.getByRole('table', { name: 'Packages affected by this change' }));
  expect(affected.getByText('Below the cost floor')).toBeInTheDocument();
  expect(affected.getByText('Above the cost floor')).toBeInTheDocument();
  expect(screen.getByRole('table', { name: 'Changes against the effective version' })).toBeInTheDocument();
});

test('a rate simulation without a price shows not applicable and omits empty tables', () => {
  render(
    <SimulatorPanel
      result={{
        ...simulationFixture,
        costFloorPaise: undefined,
        marginPercent: undefined,
        diff: undefined,
        profiles: [],
        warnings: [],
        affectedPackages: [],
      }}
    />
  );

  expect(screen.getAllByText('not applicable')).toHaveLength(2);
  expect(screen.queryByRole('table', { name: 'Usage profiles' })).toBeNull();
  expect(screen.queryByRole('list', { name: 'Warnings' })).toBeNull();
  expect(screen.getByText('No difference from the effective version.')).toBeInTheDocument();
});

test('nothing renders before a simulation exists', () => {
  const { container } = render(<SimulatorPanel result={null} />);
  expect(container).toBeEmptyDOMElement();
});

test('the diff table names added and removed fields in words', () => {
  render(
    <VersionDiff
      diff={{
        changes: [
          { path: 'a', before: '1' },
          { path: 'b', after: '2' },
        ],
      }}
    />
  );
  expect(screen.getByText('removed')).toBeInTheDocument();
  expect(screen.getByText('not set')).toBeInTheDocument();
});
