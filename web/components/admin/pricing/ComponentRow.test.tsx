// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen } from '@testing-library/react';
import { emptyComponent, PROACTIVE_COMPONENT_ID, type ComponentRowState } from '@/lib/pricing-package';
import { ComponentRow, type AvailabilityNote } from './ComponentRow';

const threads = [{ threadId: 'llm', unit: 'token', rawCostPaise: 3 }];

function show(row: ComponentRowState, availability: AvailabilityNote = 'UNCHECKED') {
  const onChange = jest.fn();
  const onRemove = jest.fn();
  render(
    <ComponentRow
      availability={availability}
      index={0}
      onChange={onChange}
      onRemove={onRemove}
      row={row}
      threads={threads}
    />
  );
  return { onChange, onRemove };
}

test('every field is labelled and edits report the whole changed row', () => {
  const row = emptyComponent('CONTENT_DRAFT');
  const { onChange, onRemove } = show(row);

  fireEvent.change(screen.getByLabelText('Component identifier 1'), { target: { value: 'POSTS' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...row, componentId: 'POSTS' });
  fireEvent.change(screen.getByLabelText('Kind 1'), { target: { value: 'SELECTED' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...row, kind: 'SELECTED' });
  fireEvent.change(screen.getByLabelText('Quantity 1'), { target: { value: '4' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...row, quantity: '4' });
  fireEvent.change(screen.getByLabelText('Cadence 1'), { target: { value: 'WEEKLY' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...row, cadence: 'WEEKLY' });
  fireEvent.change(screen.getByLabelText('Selectable maximum 1 (optional)'), { target: { value: '4' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...row, selectableMaximum: '4' });
  fireEvent.change(screen.getByLabelText('Price allocation 1 (INR)'), { target: { value: '500' } });
  expect(onChange).toHaveBeenLastCalledWith({ ...row, allocationInr: '500' });
  fireEvent.click(screen.getByLabelText('Customers may top up component 1'));
  expect(onChange).toHaveBeenLastCalledWith({ ...row, topupAllowed: true });

  fireEvent.click(screen.getByRole('button', { name: 'Add thread' }));
  expect(onChange).toHaveBeenLastCalledWith({ ...row, recipe: [{ threadId: '', unitsPerUnit: '' }] });
  fireEvent.click(screen.getByRole('button', { name: 'Remove component 1' }));
  expect(onRemove).toHaveBeenCalledTimes(1);
});

test('the proactive message row is fixed at 30 and cannot be removed', () => {
  show(emptyComponent(PROACTIVE_COMPONENT_ID));

  expect(screen.getByRole('group', { name: 'Component 1: proactive messages (fixed at 30)' })).toBeInTheDocument();
  expect(screen.getByLabelText('Quantity 1')).toHaveValue('30');
  expect(screen.getByLabelText('Quantity 1')).toHaveAttribute('readonly');
  expect(screen.getByLabelText('Component identifier 1')).toHaveAttribute('readonly');
  expect(screen.queryByRole('button', { name: 'Remove component 1' })).toBeNull();
});

test('availability is stated in words for every outcome', () => {
  const row = emptyComponent('AD_BOOST');
  const { unmount } = render(
    <ComponentRow
      availability="UNAVAILABLE"
      index={0}
      onChange={jest.fn()}
      onRemove={jest.fn()}
      row={row}
      threads={threads}
    />
  );
  expect(screen.getByText(/Not available: cannot go on sale/)).toBeInTheDocument();
  unmount();
  render(
    <ComponentRow
      availability="CHECKED"
      index={0}
      onChange={jest.fn()}
      onRemove={jest.fn()}
      row={row}
      threads={threads}
    />
  );
  expect(screen.getByText('Available at the last simulation')).toBeInTheDocument();
});
