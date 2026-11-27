// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R011
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';

// There is no customer billing API yet, so say so plainly instead of answering "Page not found".
export default function BillingPage() {
  return (
    <StateView
      actionHref="/profile"
      actionLabel="Go to Profile"
      kind="empty"
      title="Billing is not available yet"
      description="Invoices, payment methods and your allowance will appear here once billing is connected to your account. Nothing is charged without your confirmation at checkout, and a Hire price is shown in the Marketplace before you accept."
    />
  );
}
