// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-07
// Constitutional basis: C-023, C-059, C-063, C-088

import { KindPage } from '../kind-page';

export default function CouponsPage() {
  return (
    <KindPage
      current="/admin/pricing/coupons"
      intro="Discount coupons for hires and renewals. A coupon can never take the price below the cost floor."
      kind="COUPON"
      notice="Coupons are discounts only; goodwill is never wallet credit."
      title="Discount coupons"
    />
  );
}
