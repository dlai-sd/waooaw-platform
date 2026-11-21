// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { KindPage } from '../kind-page';

export default function GrantsPage() {
  return (
    <KindPage
      current="/admin/pricing/grants"
      intro="Trial and setup grants per agent. A trial grant is one per customer; a setup grant is one per relationship."
      kind="GRANT"
      title="Trial and setup grants"
    />
  );
}
