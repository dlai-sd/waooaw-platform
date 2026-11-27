import { render, screen } from '@testing-library/react';
import BillingPage from '@/app/(application)/billing/page';

it('says billing is not available yet instead of answering page not found', () => {
  render(<BillingPage />);

  expect(screen.getByRole('heading', { name: 'Billing is not available yet' })).toBeVisible();
  expect(screen.getByRole('link', { name: 'Go to Profile' })).toHaveAttribute('href', '/profile');
  expect(screen.queryByText('Page not found')).not.toBeInTheDocument();
});
