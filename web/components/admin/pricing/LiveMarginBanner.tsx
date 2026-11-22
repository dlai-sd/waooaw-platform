'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { formatInr } from '@/lib/pricing-admin-client';
import type { LiveMargin } from '@/lib/pricing-admin-types';

const reasonText = { BELOW_FLOOR: 'below the cost floor', BELOW_MINIMUM_MARGIN: 'below the minimum margin' } as const;

type Props = { margin: LiveMargin | null; status?: number | null };

// 503 is the Business Platform saying the pricing owner is not connected, so retrying will not help.
const unavailableText = 'The pricing service is not connected in this environment yet, so nothing can be checked.';

export function LiveMarginBanner({ margin, status = null }: Props) {
  if (margin === null) {
    return (
      <div className="workbench-message workbench-message-error pricing-banner" role="alert">
        <p>
          <strong>Error:</strong> Live margin could not be loaded. Treat package margins as unchecked.
        </p>
        {status === 503 ? <p className="workbench-hint">{unavailableText}</p> : null}
      </div>
    );
  }
  if (margin.breaches.length === 0) {
    return (
      <output className="workbench-message">
        <strong>Healthy:</strong> All {margin.packagesChecked} checked packages hold their margin.
      </output>
    );
  }
  return (
    <section aria-label="Live margin breaches" className="workbench-message workbench-message-error" role="alert">
      <p>
        <strong>Warning:</strong> {margin.breaches.length} of {margin.packagesChecked} packages need attention.
      </p>
      <ul className="workbench-plain-list">
        {margin.breaches.map((breach) => (
          <li key={breach.packageVersionId}>
            {breach.subjectKey} is {reasonText[breach.reason]}: price {formatInr(breach.priceInclGstPaise)}, floor{' '}
            {formatInr(breach.floorPaise)}, margin {breach.marginPercent.toFixed(1)}% against a minimum of{' '}
            {breach.minimumMarginPercent.toFixed(1)}%.
          </li>
        ))}
      </ul>
    </section>
  );
}
