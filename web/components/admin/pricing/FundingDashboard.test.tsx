// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-08
// Constitutional basis: C-023, C-059, C-063, C-088

import { render, screen, within } from '@testing-library/react';
import type { FundingDashboard as Funding, MarginDashboard as Margin } from '@/lib/pricing-admin-types';
import { FundingDashboard } from './FundingDashboard';

const cost = (componentId: string, toleranceState: 'WITHIN_TOLERANCE' | 'ALERT' | 'EXCEEDED') => ({
  componentId,
  recipeCostPaise: 1000,
  actualCostPaise: 1500,
  impliedMarginPercent: 41.5,
  toleranceState,
});

const funding: Funding = {
  generatedAt: '2026-11-20T09:00:00Z',
  spendByAccountClass: [{ accountClass: 'TRIAL', spentPaise: 12000 }],
  spendByTenant: [{ tenantRef: 'tenant-a', spentPaise: 9000 }],
  spendByCampaign: [{ campaignRef: 'DEFAULT', spentPaise: 3000 }],
  leadSpend: [{ leadRef: 'lead-7f3a', spentPaise: 700 }],
  costPerLeadPaise: 500,
  costPerConversationPaise: 1200,
  trialToHire: { trials: 20, hires: 5, conversionPercent: 25 },
  grantConsumption: [
    { grantKind: 'TRIAL', agentType: 'dma', agentVersion: 'v3', consumedPaise: 3000, grantedPaise: 5000 },
  ],
  componentCost: [cost('POSTS', 'WITHIN_TOLERANCE'), cost('ADS', 'ALERT'), cost('MONITOR', 'EXCEEDED')],
  events: [
    { eventKind: 'EXHAUSTION', count: 2 },
    { eventKind: 'TOPUP', count: 1 },
  ],
  breakers: [{ breaker: 'acquisition', state: 'HALF_OPEN' }],
  liveMarginBreaches: 1,
};

const margin: Margin = {
  generatedAt: '2026-11-20T09:00:00Z',
  packages: [
    {
      packageVersionId: 'p1',
      subjectKey: 'package:dma|v3|STARTER',
      priceInclGstPaise: 200000,
      basePricePaise: 169492,
      costFloorPaise: 80000,
      marginPercent: 52.8,
      minimumMarginPercent: 55,
    },
    {
      packageVersionId: 'p2',
      subjectKey: 'package:dma|v3|PRO',
      priceInclGstPaise: 400000,
      basePricePaise: 338983,
      costFloorPaise: 90000,
      marginPercent: 73.4,
      minimumMarginPercent: 55,
    },
  ],
  componentCost: [],
  liveMarginBreaches: 1,
};

test('every funding figure is shown with words for state', () => {
  render(<FundingDashboard from="2026-11-01" funding={funding} margin={margin} to="2026-11-20" />);

  const section = within(screen.getByRole('region', { name: 'Funding' }));
  expect(section.getByText('INR 5.00')).toBeInTheDocument();
  expect(section.getByText('INR 12.00')).toBeInTheDocument();
  expect(section.getByText('5 hires from 20 trials (25.0%)')).toBeInTheDocument();
  expect(section.getByRole('table', { name: 'Spend by account class' })).toHaveTextContent('TRIAL');
  expect(section.getByRole('table', { name: 'Spend by tenant' })).toHaveTextContent('tenant-a');
  expect(section.getByRole('table', { name: 'Spend by campaign' })).toHaveTextContent('DEFAULT');
  expect(section.getByRole('table', { name: 'Spend by lead' })).toHaveTextContent('lead-7f3a');
  expect(section.getByRole('table', { name: 'Grant consumption' })).toHaveTextContent('INR 30.00');
  const costs = within(section.getByRole('table', { name: 'Actual against recipe cost' }));
  expect(costs.getByText('Within tolerance')).toBeInTheDocument();
  expect(costs.getByText(/^Alert:/)).toBeInTheDocument();
  expect(costs.getByText(/^Exceeded:/)).toBeInTheDocument();
  expect(section.getByRole('list', { name: 'Events' })).toHaveTextContent('Allowance exhausted: 2');
  expect(section.getByRole('list', { name: 'Events' })).toHaveTextContent('Top-ups bought: 1');
  expect(section.getByRole('list', { name: 'Breakers' })).toHaveTextContent('acquisition: half open');
});

test('margin rows state whether the minimum is met in words', () => {
  render(<FundingDashboard from="" funding={funding} margin={margin} to="" />);

  const table = within(screen.getByRole('table', { name: 'Package margins' }));
  expect(table.getByText('Below the minimum margin')).toBeInTheDocument();
  expect(table.getByText('Meets the minimum margin')).toBeInTheDocument();
  expect(screen.getByText('No component cost has been recorded in this period.')).toBeInTheDocument();
});

test('the period form is a labelled GET form that keeps the chosen dates', () => {
  render(<FundingDashboard from="2026-11-01" funding={funding} margin={margin} to="2026-11-20" />);

  const form = screen.getByRole('form', { name: 'Reporting period' });
  expect(form).toHaveAttribute('method', 'get');
  expect(screen.getByLabelText('From')).toHaveValue('2026-11-01');
  expect(screen.getByLabelText('To')).toHaveValue('2026-11-20');
});

test('empty reports say so instead of showing blank tables', () => {
  render(
    <FundingDashboard
      from=""
      funding={{
        ...funding,
        spendByAccountClass: [],
        spendByTenant: [],
        spendByCampaign: [],
        leadSpend: [],
        grantConsumption: [],
        componentCost: [],
        events: [],
        breakers: [],
      }}
      margin={{ ...margin, packages: [] }}
      to=""
    />
  );

  expect(screen.getByText('No spend by account class in this period.')).toBeInTheDocument();
  expect(screen.getByText('No grants have been consumed in this period.')).toBeInTheDocument();
  expect(screen.getByText('No exhaustion or top-up events in this period.')).toBeInTheDocument();
  expect(screen.getByText('No breaker state is reported.')).toBeInTheDocument();
  expect(screen.getByText('No packages are effective yet.')).toBeInTheDocument();
  expect(screen.queryByRole('table')).toBeNull();
});

test('a report that failed to load is announced and the other report still shows', () => {
  render(<FundingDashboard from="" funding={null} margin={margin} to="" />);

  expect(screen.getByRole('alert')).toHaveTextContent('The funding report could not be loaded.');
  expect(screen.getByRole('table', { name: 'Package margins' })).toBeInTheDocument();
});

test('a failed margin report is announced too', () => {
  render(<FundingDashboard from="" funding={funding} margin={null} to="" />);
  expect(screen.getByRole('alert')).toHaveTextContent('The margin report could not be loaded.');
});
