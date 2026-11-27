// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { formatInr } from '@/lib/pricing-admin-client';
import type { Simulation } from '@/lib/pricing-admin-types';
import { VersionDiff } from './VersionDiff';

function money(value: number | undefined): string {
  return value === undefined ? 'not applicable' : formatInr(value);
}

export function SimulatorPanel({ result }: { result: Simulation | null }) {
  if (result === null) return null;
  return (
    <section aria-label="Simulation result" className="workbench-section">
      <h3>Simulation</h3>
      <dl>
        <dt>Cost floor</dt>
        <dd>{money(result.costFloorPaise)}</dd>
        <dt>Base price</dt>
        <dd>{money(result.basePricePaise)}</dd>
        <dt>GST</dt>
        <dd>{money(result.gstPaise)}</dd>
        <dt>Price including GST</dt>
        <dd>{money(result.priceInclGstPaise)}</dd>
        <dt>Margin</dt>
        <dd>{result.marginPercent === undefined ? 'not applicable' : `${result.marginPercent.toFixed(1)}%`}</dd>
        <dt>Lowest compliant price</dt>
        <dd>{money(result.minimumCompliantPricePaise)}</dd>
      </dl>
      {result.profiles.length > 0 ? (
        <table aria-label="Usage profiles">
          <thead>
            <tr>
              <th scope="col">Profile</th>
              <th scope="col">Monthly cost</th>
              <th scope="col">Margin</th>
              <th
                scope="col"
                title="The most the platform could spend on day one if the customer uses everything allowed, then leaves on day two"
              >
                Day-one exposure
              </th>
              <th scope="col" title="The part of the price refunded if the customer leaves on day two">
                Pro-rata refund
              </th>
            </tr>
          </thead>
          <tbody>
            {result.profiles.map((profile) => (
              <tr key={`${profile.profile}:${profile.personaName ?? ''}`}>
                <th scope="row">{profile.personaName ?? profile.profile}</th>
                <td>{formatInr(profile.expectedMonthlyCostPaise)}</td>
                <td>{profile.marginPercent.toFixed(1)}%</td>
                <td>{money(profile.dayOneExposurePaise)}</td>
                <td>{money(profile.proRataRefundPaise)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {result.warnings.length > 0 ? (
        <ul aria-label="Warnings" className="workbench-plain-list">
          {result.warnings.map((warning) => (
            <li key={`${warning.code}:${warning.componentId ?? ''}`}>
              <strong>Warning:</strong> {warning.message}
            </li>
          ))}
        </ul>
      ) : null}
      {result.affectedPackages.length > 0 ? (
        <table aria-label="Packages affected by this change">
          <thead>
            <tr>
              <th scope="col">Package</th>
              <th scope="col">Floor now</th>
              <th scope="col">Floor after</th>
              <th scope="col">Price</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {result.affectedPackages.map((affected) => (
              <tr key={affected.packageVersionId}>
                <th scope="row">{affected.subjectKey}</th>
                <td>{formatInr(affected.currentFloorPaise)}</td>
                <td>{formatInr(affected.newFloorPaise)}</td>
                <td>{formatInr(affected.priceInclGstPaise)}</td>
                <td>{affected.belowFloor ? 'Below the cost floor' : 'Above the cost floor'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <h4>Differences</h4>
      <VersionDiff diff={result.diff} />
    </section>
  );
}
