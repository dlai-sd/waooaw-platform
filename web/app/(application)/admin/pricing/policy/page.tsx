// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { KindPage } from '../kind-page';

export default function PolicyPage() {
  return (
    <KindPage
      current="/admin/pricing/policy"
      intro="Platform-wide pricing policy: minimum margin, payment grace, notice periods, cost tolerances and large-change guards."
      kind="POLICY"
      title="Pricing policy"
    />
  );
}
