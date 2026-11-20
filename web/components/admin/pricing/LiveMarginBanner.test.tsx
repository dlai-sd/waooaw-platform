// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { render, screen } from '@testing-library/react';
import { LiveMarginBanner } from './LiveMarginBanner';

test('a failed load is an error, not silence', () => {
  render(<LiveMarginBanner margin={null} />);
  expect(screen.getByRole('alert')).toHaveTextContent('Live margin could not be loaded.');
});

test('no breaches reads as healthy in words', () => {
  render(<LiveMarginBanner margin={{ computedAt: 'now', packagesChecked: 3, breaches: [] }} />);
  expect(screen.getByRole('status')).toHaveTextContent('Healthy: All 3 checked packages hold their margin.');
});

test('each breach names the package, the reason and the numbers', () => {
  render(
    <LiveMarginBanner
      margin={{
        computedAt: 'now',
        packagesChecked: 2,
        breaches: [
          {
            packageVersionId: 'a',
            subjectKey: 'package:dma|v3|STARTER',
            floorPaise: 210000,
            priceInclGstPaise: 200000,
            marginPercent: -5,
            minimumMarginPercent: 55,
            reason: 'BELOW_FLOOR',
          },
          {
            packageVersionId: 'b',
            subjectKey: 'package:dma|v3|PRO',
            floorPaise: 100000,
            priceInclGstPaise: 150000,
            marginPercent: 40,
            minimumMarginPercent: 55,
            reason: 'BELOW_MINIMUM_MARGIN',
          },
        ],
      }}
    />
  );

  const alert = screen.getByRole('alert');
  expect(alert).toHaveTextContent('Warning: 2 of 2 packages need attention.');
  expect(alert).toHaveTextContent(
    'package:dma|v3|STARTER is below the cost floor: price INR 2,000.00, floor INR 2,100.00, margin -5.0%'
  );
  expect(alert).toHaveTextContent('package:dma|v3|PRO is below the minimum margin');
});
