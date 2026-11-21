// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import type { RecipeRow } from '@/lib/pricing-package';
import { RecipeEditor } from './RecipeEditor';

const threads = [
  { threadId: 'llm', unit: '1k tokens', rawCostPaise: 250 },
  { threadId: 'sms', unit: 'message', rawCostPaise: 40 },
];

function Harness({ initial }: { initial: RecipeRow[] }) {
  const [rows, setRows] = useState(initial);
  return (
    <>
      <RecipeEditor idPrefix="c1" onChange={setRows} rows={rows} threads={threads} />
      <output aria-label="state">{JSON.stringify(rows)}</output>
    </>
  );
}

test('an empty recipe explains itself and rows can be added, picked, edited and removed', () => {
  render(<Harness initial={[]} />);
  expect(screen.getByText(/No threads yet/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'Add thread' }));
  fireEvent.change(screen.getByLabelText('Thread 1'), { target: { value: 'llm' } });
  fireEvent.change(screen.getByLabelText('Units per unit 1'), { target: { value: '3' } });

  expect(screen.getByLabelText('state')).toHaveTextContent('[{"threadId":"llm","unitsPerUnit":"3"}]');
  expect(screen.getByText('Raw unit cost INR 2.50 per 1k tokens')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'Remove thread 1' }));
  expect(screen.getByLabelText('state')).toHaveTextContent('[]');
});

test('a stored thread missing from the catalogue stays visible and says so', () => {
  render(
    <Harness
      initial={[
        { threadId: 'legacy', unitsPerUnit: '1' },
        { threadId: '', unitsPerUnit: '' },
      ]}
    />
  );

  expect(screen.getByRole('option', { name: 'legacy (not in the catalogue)' })).toBeInTheDocument();
  expect(screen.getAllByText('No live unit cost for this thread')).toHaveLength(2);
});
