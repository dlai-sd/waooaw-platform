// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { KindPage } from '../kind-page';

export default function BudgetsPage() {
  return (
    <KindPage
      current="/admin/pricing/budgets"
      intro="Spend budgets and the environment ceiling. Lowering a budget takes effect at once; raising one needs the Founder."
      kind="BUDGET"
      title="Spend budgets and ceilings"
    />
  );
}
