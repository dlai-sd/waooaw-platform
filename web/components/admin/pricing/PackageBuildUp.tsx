'use client';

// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R018
// Constitutional basis: C-023, C-049, C-059, C-063

import { formatInr } from '@/lib/pricing-admin-client';
import type { Simulation } from '@/lib/pricing-admin-types';

type Props = {
  simulation: Simulation | null;
  typedPriceInclGstPaise: number | null;
  onUseSuggestedPrice: (paise: number) => void;
};

const statusNotes = {
  COMPLETE: 'Every cost line is known and authorized.',
  INCOMPLETE:
    'Incomplete: some costs are unknown or their rates are not yet authorized, so the real cost is higher. Do not treat this as a final price.',
  UNUSABLE:
    'No suggestion: no cost is known yet, or there is no target margin for this package and no policy minimum margin.',
} as const;

export function PackageBuildUp({ simulation, typedPriceInclGstPaise, onUseSuggestedPrice }: Props) {
  const buildUp = simulation?.buildUp;
  if (!simulation || !buildUp) {
    return (
      <section aria-label="Price build-up" className="workbench-stack package-build-up">
        <h4>Price build-up</h4>
        <p className="workbench-hint">
          Save the draft, then press Simulate. The cost lines, your target margin and a suggested price appear here.
          Saving a change clears an older build-up, so what you see always matches the saved draft.
        </p>
      </section>
    );
  }
  const suggested = buildUp.suggestedPriceInclGstPaise;
  return (
    <section aria-label="Price build-up" className="workbench-stack package-build-up">
      <h4>Price build-up</h4>
      <table aria-label="Cost lines">
        <thead>
          <tr>
            <th scope="col">Component</th>
            <th scope="col">Ingredient</th>
            <th scope="col">Quantity</th>
            <th scope="col">Cost each, with markup</th>
            <th scope="col">Line cost</th>
          </tr>
        </thead>
        <tbody>
          {buildUp.costLines.map((line) => (
            <tr key={`${line.componentId}|${line.threadId}`}>
              <th scope="row">{line.componentId}</th>
              <td>
                {line.threadId}
                {line.authorized ? '' : ' (rate not authorized)'}
              </td>
              <td>{line.quantity * line.unitsPerUnit}</td>
              <td>{line.unitCostPaise === undefined ? 'Unknown' : formatInr(line.unitCostPaise)}</td>
              <td>{line.lineCostPaise === undefined ? 'Unknown' : formatInr(line.lineCostPaise)}</td>
            </tr>
          ))}
          <tr>
            <th scope="row">Infrastructure share</th>
            <td colSpan={3} />
            <td>{formatInr(buildUp.infrastructureSharePaise)}</td>
          </tr>
          <tr>
            <th scope="row">Cost floor (total cost)</th>
            <td colSpan={3} />
            <td>{formatInr(buildUp.costFloorPaise)}</td>
          </tr>
        </tbody>
      </table>
      {buildUp.uncostedComponentIds.length > 0 ? (
        <p className="workbench-hint">
          No ingredient lines yet for: {buildUp.uncostedComponentIds.join(', ')}. Their cost is not in the total.
        </p>
      ) : null}
      <p>
        Target margin: {buildUp.targetMarginPercent === undefined ? 'none set' : `${buildUp.targetMarginPercent}%`}.
        Suggested price including GST: {suggested === undefined ? 'none' : formatInr(suggested)}.
      </p>
      <p className="workbench-hint">{statusNotes[buildUp.suggestionStatus]}</p>
      <p>
        Your price: {typedPriceInclGstPaise === null ? 'not entered' : formatInr(typedPriceInclGstPaise)}. Only the
        price you type and save is used.
      </p>
      {suggested !== undefined && buildUp.suggestionStatus === 'COMPLETE' ? (
        <button className="secondary-link" onClick={() => onUseSuggestedPrice(suggested)} type="button">
          Put the suggested price in the price box
        </button>
      ) : null}
    </section>
  );
}
