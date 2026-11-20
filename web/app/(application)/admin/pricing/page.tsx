// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { ExportImport } from '@/components/admin/pricing/ExportImport';
import { LiveMarginBanner } from '@/components/admin/pricing/LiveMarginBanner';
import { PricingPageFrame } from '@/components/admin/pricing/PricingPageFrame';
import { SafetyControls } from '@/components/admin/pricing/SafetyControls';
import { loadVersions, requirePricingPage, wireShape } from '@/lib/pricing-admin-pages';
import { pricingApis } from '@/lib/pricing-admin-server';
import { logServerFailure } from '@/lib/server-failure';
import type { LiveMargin } from '@/lib/pricing-admin-types';

async function loadLiveMargin(accessToken: string): Promise<LiveMargin | null> {
  try {
    return wireShape<LiveMargin>(await pricingApis(accessToken).reports.getPricingLiveMargin());
  } catch (error) {
    logServerFailure('web.admin.pricing.live_margin_failed', error);
    return null;
  }
}

export default async function PricingOverviewPage() {
  const { accessToken } = await requirePricingPage();
  const [margin, packages, grants] = await Promise.all([
    loadLiveMargin(accessToken),
    loadVersions(accessToken, 'PACKAGE'),
    loadVersions(accessToken, 'GRANT'),
  ]);
  return (
    <PricingPageFrame
      current="/admin/pricing"
      intro="Rates, packages, grants, budgets and coupons are versioned. Administrators draft; only the Founder authorizes."
      title="Pricing"
    >
      <LiveMarginBanner margin={margin} />
      <SafetyControls
        grants={(grants ?? []).filter((version) => version.state === 'EFFECTIVE')}
        packages={(packages ?? []).filter((version) => version.state === 'EFFECTIVE')}
      />
      <ExportImport />
    </PricingPageFrame>
  );
}
