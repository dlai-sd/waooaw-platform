'use client';

// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R022
// Constitutional basis: C-023, C-059, C-063

import { formatInr, paiseFromInr } from '@/lib/pricing-admin-client';
import type { ComponentRowState } from '@/lib/pricing-package';
import type { AvailabilityNote } from './ComponentRow';

type Props = {
  components: ComponentRowState[];
  selectedKey: string | undefined;
  availabilityFor: (componentId: string) => AvailabilityNote;
  onSelect: (key: string) => void;
};

const availabilityShort: Record<AvailabilityNote, string> = {
  UNAVAILABLE: 'Not available',
  CHECKED: 'Available',
  UNCHECKED: 'Not checked',
};

// Every component is one row; the Founder picks one row to edit in the panel below, so the page stays short.
export function ComponentTable({ components, selectedKey, availabilityFor, onSelect }: Props) {
  return (
    <div className="package-table-wrap">
      <table aria-label="Package components" className="package-components-table">
        <thead>
          <tr>
            <th scope="col">No.</th>
            <th scope="col">Component</th>
            <th scope="col">Kind</th>
            <th className="package-numeric" scope="col">
              Quantity
            </th>
            <th scope="col">Cadence</th>
            <th className="package-numeric" scope="col">
              Allocation
            </th>
            <th scope="col">Ingredients</th>
            <th scope="col">Availability</th>
            <th scope="col">
              <span className="package-visually-hidden">Edit</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {components.map((row, index) => {
            const selected = row.key === selectedKey;
            const allocation = paiseFromInr(row.allocationInr);
            const ingredients = row.recipe.map((entry) => entry.threadId).filter((id) => id !== '');
            return (
              <tr
                aria-current={selected ? 'true' : undefined}
                className={selected ? 'package-row-selected' : undefined}
                key={row.key}
              >
                <td>{index + 1}</td>
                <th scope="row">{row.componentId.trim() === '' ? 'New component' : row.componentId}</th>
                <td>{row.kind}</td>
                <td className="package-numeric">{row.quantity === '' ? '-' : row.quantity}</td>
                <td>{row.cadence}</td>
                <td className="package-numeric">{allocation === null ? '-' : formatInr(allocation)}</td>
                <td>{ingredients.length === 0 ? 'None yet' : ingredients.join(', ')}</td>
                <td>{availabilityShort[availabilityFor(row.componentId)]}</td>
                <td>
                  <button
                    aria-label={`Edit component ${index + 1}`}
                    aria-pressed={selected}
                    className="secondary-link"
                    onClick={() => onSelect(row.key)}
                    type="button"
                  >
                    {selected ? 'Editing' : 'Edit'}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
