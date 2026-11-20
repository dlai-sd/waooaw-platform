// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { KindPage } from '../kind-page';

export default function RatesPage() {
  return (
    <KindPage
      current="/admin/pricing/rates"
      intro="Raw cost per unit for each thread. Packages are costed from the effective rates."
      kind="RATE"
      notice="Administrators prepare drafts. Only the Founder authorizes, with a fresh multi-factor sign-in."
      title="Thread rates"
    />
  );
}
