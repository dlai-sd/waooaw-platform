// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063, C-065

import { AccessApprovals } from '@/components/admin/access/AccessApprovals';

export const dynamic = 'force-dynamic';

export default function FounderAccessPage() {
  return <AccessApprovals />;
}
