'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { useRef } from 'react';
import { formatInr } from '@/lib/pricing-admin-client';
import type { CatalogueThread } from '@/lib/pricing-admin-types';
import type { RecipeRow } from '@/lib/pricing-package';

type Props = {
  idPrefix: string;
  rows: RecipeRow[];
  threads: CatalogueThread[];
  onChange: (rows: RecipeRow[]) => void;
  // The component card puts its own Add thread button in its footer row to save a line.
  hideAdd?: boolean;
};

export function RecipeEditor({ idPrefix, rows, threads, onChange, hideAdd = false }: Props) {
  const keys = useRef<string[]>([]);
  const counter = useRef(0);
  while (keys.current.length < rows.length) {
    counter.current += 1;
    keys.current.push(`row-${counter.current}`);
  }
  keys.current.length = rows.length;
  const update = (index: number, patch: Partial<RecipeRow>) =>
    onChange(rows.map((row, position) => (position === index ? { ...row, ...patch } : row)));

  return (
    <fieldset className="package-recipe">
      <legend>Cost recipe</legend>
      {rows.length === 0 ? (
        <p className="workbench-hint">No threads yet. A recipe lists what one unit consumes.</p>
      ) : null}
      {rows.map((row, index) => {
        const thread = threads.find((candidate) => candidate.threadId === row.threadId);
        return (
          <div className="package-recipe-row" key={keys.current[index]}>
            <div className="package-field">
              <label htmlFor={`${idPrefix}-thread-${index}`}>Thread {index + 1}</label>
              <select
                id={`${idPrefix}-thread-${index}`}
                onChange={(event) => update(index, { threadId: event.target.value })}
                value={row.threadId}
              >
                <option value="">Choose a thread</option>
                {row.threadId !== '' && thread === undefined ? (
                  <option value={row.threadId}>{row.threadId} (not in the catalogue)</option>
                ) : null}
                {threads.map((candidate) => (
                  <option key={candidate.threadId} value={candidate.threadId}>
                    {candidate.threadId}
                  </option>
                ))}
              </select>
            </div>
            <div className="package-field">
              <label htmlFor={`${idPrefix}-units-${index}`}>Units per unit {index + 1}</label>
              <input
                id={`${idPrefix}-units-${index}`}
                inputMode="numeric"
                onChange={(event) => update(index, { unitsPerUnit: event.target.value })}
                type="text"
                value={row.unitsPerUnit}
              />
            </div>
            <span className="workbench-hint package-recipe-cost">
              {thread
                ? `Raw unit cost ${formatInr(thread.rawCostPaise)} per ${thread.unit}`
                : 'No live unit cost for this thread'}
            </span>
            <button
              aria-label={`Remove thread ${index + 1}`}
              className="secondary-link"
              onClick={() => {
                keys.current.splice(index, 1);
                onChange(rows.filter((_, position) => position !== index));
              }}
              type="button"
            >
              Remove
            </button>
          </div>
        );
      })}
      {hideAdd ? null : (
        <button
          className="secondary-link"
          onClick={() => onChange([...rows, { threadId: '', unitsPerUnit: '' }])}
          type="button"
        >
          Add thread
        </button>
      )}
    </fieldset>
  );
}
