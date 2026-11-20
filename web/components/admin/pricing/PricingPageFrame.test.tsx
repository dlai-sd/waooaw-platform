// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { render, screen } from '@testing-library/react';
import { PricingPageFrame } from './PricingPageFrame';

test('the frame titles the page, marks the current section and renders its content', () => {
  render(
    <PricingPageFrame current="/admin/pricing/rates" intro="Thread rates." title="Rates">
      <p>content</p>
    </PricingPageFrame>
  );

  expect(screen.getByRole('heading', { level: 1, name: 'Rates' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Rates' })).toHaveAttribute('aria-current', 'page');
  expect(screen.getByRole('link', { name: 'Packages' })).not.toHaveAttribute('aria-current');
  expect(screen.getByRole('navigation', { name: 'Pricing sections' })).toBeInTheDocument();
  expect(screen.getAllByRole('link')).toHaveLength(8);
  expect(screen.getByText('content')).toBeInTheDocument();
});
