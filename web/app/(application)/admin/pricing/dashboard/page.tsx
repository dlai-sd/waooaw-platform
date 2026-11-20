// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-08
// Constitutional basis: C-023, C-059, C-063, C-088

import { FundingDashboard } from '@/components/admin/pricing/FundingDashboard';
import { PricingPageFrame } from '@/components/admin/pricing/PricingPageFrame';
import { periodFrom, requirePricingPage, wireShape } from '@/lib/pricing-admin-pages';
import { pricingApis } from '@/lib/pricing-admin-server';
import { logServerFailure } from '@/lib/server-failure';
import type { FundingDashboard as Funding, MarginDashboard as Margin } from '@/lib/pricing-admin-types';

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

const startOfDay = (value: string) => (value ? new Date(`${value}T00:00:00Z`) : undefined);

async function attempt<T>(load: () => Promise<unknown>): Promise<T | null> {
  try {
    return wireShape<T>(await load());
  } catch (error) {
    logServerFailure('web.admin.pricing.dashboard_failed', error);
    return null;
  }
}

export default async function PricingDashboardPage({ searchParams }: Props) {
  const query = await searchParams;
  const { accessToken } = await requirePricingPage();
  const from = periodFrom(query.from);
  const to = periodFrom(query.to);
  const { reports } = pricingApis(accessToken);
  const period = { from: startOfDay(from), to: startOfDay(to) };
  const [funding, margin] = await Promise.all([
    attempt<Funding>(() => reports.getPricingFundingDashboard(period)),
    attempt<Margin>(() => reports.getPricingMarginDashboard(period)),
  ]);
  return (
    <PricingPageFrame
      current="/admin/pricing/dashboard"
      intro="Spend by account class, tenant, campaign and pseudonymous lead, with actual against recipe cost and package margins. Aggregates only."
      title="Funding and margin"
    >
      <FundingDashboard from={from} funding={funding} margin={margin} to={to} />
    </PricingPageFrame>
  );
}
