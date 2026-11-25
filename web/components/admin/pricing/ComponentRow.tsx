'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import {
  cadences,
  componentKinds,
  PROACTIVE_COMPONENT_ID,
  PROACTIVE_QUANTITY,
  type ComponentRowState,
} from '@/lib/pricing-package';
import type { CatalogueThread } from '@/lib/pricing-admin-types';
import { RecipeEditor } from './RecipeEditor';

export type AvailabilityNote = 'UNAVAILABLE' | 'CHECKED' | 'UNCHECKED';

type Props = {
  index: number;
  row: ComponentRowState;
  threads: CatalogueThread[];
  availability: AvailabilityNote;
  onChange: (row: ComponentRowState) => void;
  onRemove: () => void;
};

const availabilityText: Record<AvailabilityNote, string> = {
  UNAVAILABLE: 'Not available: cannot go on sale until the agent releases it',
  CHECKED: 'Available at the last simulation',
  UNCHECKED: 'Availability is checked when you simulate',
};

export function ComponentRow({ index, row, threads, availability, onChange, onRemove }: Props) {
  const number = index + 1;
  const fixed = row.componentId === PROACTIVE_COMPONENT_ID;
  const id = `component-${row.key}`;
  const patch = (changes: Partial<ComponentRowState>) => onChange({ ...row, ...changes });

  return (
    <fieldset className="package-component">
      <legend>
        {fixed ? `Component ${number}: proactive messages (fixed at ${PROACTIVE_QUANTITY})` : `Component ${number}`}
      </legend>
      <div className="package-component-fields">
        <div className="package-field package-field-wide">
          <label htmlFor={`${id}-id`}>Component identifier {number}</label>
          <input
            id={`${id}-id`}
            onChange={(event) => patch({ componentId: event.target.value })}
            readOnly={fixed}
            type="text"
            value={row.componentId}
          />
        </div>
        <div className="package-field">
          <label htmlFor={`${id}-kind`}>Kind {number}</label>
          <select id={`${id}-kind`} onChange={(event) => patch({ kind: event.target.value })} value={row.kind}>
            {componentKinds.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </select>
        </div>
        <div className="package-field">
          <label htmlFor={`${id}-quantity`}>Quantity {number}</label>
          <input
            id={`${id}-quantity`}
            inputMode="numeric"
            onChange={(event) => patch({ quantity: event.target.value })}
            readOnly={fixed}
            type="text"
            value={fixed ? String(PROACTIVE_QUANTITY) : row.quantity}
          />
        </div>
        <div className="package-field">
          <label htmlFor={`${id}-cadence`}>Cadence {number}</label>
          <select id={`${id}-cadence`} onChange={(event) => patch({ cadence: event.target.value })} value={row.cadence}>
            {cadences.map((cadence) => (
              <option key={cadence} value={cadence}>
                {cadence}
              </option>
            ))}
          </select>
        </div>
        <div className="package-field">
          <label htmlFor={`${id}-maximum`}>Selectable maximum {number} (optional)</label>
          <input
            id={`${id}-maximum`}
            inputMode="numeric"
            onChange={(event) => patch({ selectableMaximum: event.target.value })}
            type="text"
            value={row.selectableMaximum}
          />
        </div>
        <div className="package-field">
          <label htmlFor={`${id}-allocation`}>Price allocation {number} (INR)</label>
          <input
            id={`${id}-allocation`}
            inputMode="decimal"
            onChange={(event) => patch({ allocationInr: event.target.value })}
            type="text"
            value={row.allocationInr}
          />
        </div>
      </div>
      <RecipeEditor
        hideAdd
        idPrefix={id}
        onChange={(recipe) => patch({ recipe })}
        rows={row.recipe}
        threads={threads}
      />
      <div className="package-component-footer">
        <p className="workbench-hint">{availabilityText[availability]}</p>
        <button
          className="secondary-link"
          onClick={() => patch({ recipe: [...row.recipe, { threadId: '', unitsPerUnit: '' }] })}
          type="button"
        >
          Add thread
        </button>
        <label className="package-check">
          <input
            checked={row.topupAllowed}
            onChange={(event) => patch({ topupAllowed: event.target.checked })}
            type="checkbox"
          />
          Customers may top up component {number}
        </label>
        {fixed ? null : (
          <button aria-label={`Remove component ${number}`} className="secondary-link" onClick={onRemove} type="button">
            Remove component
          </button>
        )}
      </div>
    </fieldset>
  );
}
