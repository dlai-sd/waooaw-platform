// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R022
// Constitutional basis: C-023, C-059, C-063

import { fireEvent, render, screen, within } from '@testing-library/react';
import type { ComponentRowState } from '@/lib/pricing-package';
import { ComponentTable } from './ComponentTable';

const row = (key: string, componentId: string, patch: Partial<ComponentRowState> = {}): ComponentRowState => ({
  key,
  componentId,
  kind: 'COUNTED',
  quantity: '4',
  cadence: 'SPREAD',
  selectableMaximum: '',
  allocationInr: '400',
  topupAllowed: false,
  recipe: [{ threadId: 'llm', unitsPerUnit: '1' }],
  ...patch,
});

test('each component is one row with its numbers, and the selected one is marked', () => {
  render(
    <ComponentTable
      availabilityFor={(id) => (id === 'AD_BOOST' ? 'UNAVAILABLE' : 'CHECKED')}
      components={[row('a', 'CONTENT_DRAFT'), row('b', 'AD_BOOST', { allocationInr: '200', recipe: [] })]}
      onSelect={jest.fn()}
      selectedKey="b"
    />
  );

  const rows = within(screen.getByRole('table', { name: 'Package components' })).getAllByRole('row');
  expect(rows).toHaveLength(3);
  expect(rows[1]).toHaveTextContent('CONTENT_DRAFT');
  expect(rows[1]).toHaveTextContent('INR 400.00');
  expect(rows[1]).toHaveTextContent('llm');
  expect(rows[1]).toHaveTextContent('Available');
  expect(rows[2]).toHaveTextContent('AD_BOOST');
  expect(rows[2]).toHaveTextContent('None yet');
  expect(rows[2]).toHaveTextContent('Not available');
  expect(rows[2]).toHaveAttribute('aria-current', 'true');
  expect(rows[1]).not.toHaveAttribute('aria-current');
});

test('choosing Edit selects that component, and an unfinished row says so instead of hiding', () => {
  const onSelect = jest.fn();
  render(
    <ComponentTable
      availabilityFor={() => 'UNCHECKED'}
      components={[row('a', 'CONTENT_DRAFT'), row('b', '', { quantity: '', allocationInr: '', recipe: [] })]}
      onSelect={onSelect}
      selectedKey="a"
    />
  );

  expect(screen.getByRole('button', { name: 'Edit component 1' })).toHaveTextContent('Editing');
  expect(screen.getByText('New component')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Edit component 2' }));
  expect(onSelect).toHaveBeenCalledWith('b');
});
