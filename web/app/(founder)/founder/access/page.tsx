// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004; work-contracts/WC-167-acceptance-demo-readiness.md WC167-R006
// Constitutional basis: C-009, C-023, C-059, C-063, C-065

import { AccessApprovals } from '@/components/admin/access/AccessApprovals';

export const dynamic = 'force-dynamic';

export default function FounderAccessPage() {
  return (
    <section aria-labelledby="founder-access-title" className="portal-page providers-admin access-page">
      <header className="portal-heading">
        <p className="eyebrow">Founder</p>
        <h1 id="founder-access-title">Staff access</h1>
        <p>Approve or reject requests for staff roles and see who holds one. Every decision is recorded.</p>
      </header>
      <AccessApprovals />
    </section>
  );
}
