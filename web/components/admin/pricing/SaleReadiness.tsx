// Implements: work-contracts/WC-172-safe-to-charge-real-customers.md (Demo defect repairs: why a package is not on sale)
// Constitutional basis: C-023, C-049, C-059

import { type PackageState, allocationTotalPaise, buildPackage } from '@/lib/pricing-package';
import { paiseFromInr } from '@/lib/pricing-admin-client';
import type { Simulation } from '@/lib/pricing-admin-types';

type Props = { state: PackageState; simulation: Simulation | null; versionState: string | null };

const past = (versionState: string | null, ...states: string[]) =>
  versionState !== null && states.includes(versionState);

/** Plain list of what still stands between a draft and being on sale, so a package that is not offered is never a mystery. */
export function SaleReadiness({ state, simulation, versionState }: Props) {
  const built = buildPackage(state);
  const price = paiseFromInr(state.priceInr);
  const allocated = allocationTotalPaise(state.components);
  const unavailable = (simulation?.warnings ?? []).filter(
    (warning) => warning.code === 'PACKAGE_COMPONENT_NOT_AVAILABLE'
  );
  const checks: Array<{ label: string; done: boolean; hint: string }> = [
    {
      label: 'Details are complete',
      done: built.ok,
      hint: built.ok ? '' : 'Fill the missing details on the Details tab and save.',
    },
    {
      label: 'Component prices add up to the package price',
      done: price !== null && allocated === price,
      hint: 'Share the whole price across the components on the Components tab.',
    },
    {
      label: 'Simulated, and every component is available',
      done: simulation !== null && unavailable.length === 0,
      hint:
        simulation === null
          ? 'Run the simulation below. It also checks the margin.'
          : `Not available yet: ${unavailable.map((warning) => warning.componentId ?? 'a component').join(', ')}.`,
    },
    {
      label: 'Submitted to the Founder',
      done: past(versionState, 'SUBMITTED', 'AUTHORIZED', 'EFFECTIVE'),
      hint: 'Submit it after the simulation.',
    },
    {
      label: 'Authorized by the Founder',
      done: past(versionState, 'AUTHORIZED', 'EFFECTIVE'),
      hint: 'Only the Founder authorizes, with a fresh multi-factor sign-in.',
    },
    {
      label: 'On sale (in force)',
      done: past(versionState, 'EFFECTIVE'),
      hint: 'It goes on sale from its effective time. Until then customers cannot hire it.',
    },
  ];
  const next = checks.find((check) => !check.done);
  return (
    <section aria-label="What stops this going on sale" className="workbench-section">
      <h3>What stops this going on sale</h3>
      <ul className="workbench-plain-list">
        {checks.map((check) => (
          <li key={check.label}>
            <strong>{check.done ? 'Done' : 'To do'}</strong>: {check.label}
            {!check.done && check === next && check.hint ? ` — ${check.hint}` : ''}
          </li>
        ))}
      </ul>
      {next ? null : <p className="workbench-hint">Nothing stops this package. Customers can hire it.</p>}
    </section>
  );
}
