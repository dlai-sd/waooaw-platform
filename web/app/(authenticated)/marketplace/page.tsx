// Implements: work-contracts/WC-084-auth-readiness-and-customer-portal-plan.md §8.6 Marketplace
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { StateView } from '@/components/system/StateView';
import { getRequestI18n } from '@/lib/i18n-server';
import { portalMessages } from '@/lib/portal-i18n';

export default async function MarketplacePage() {
  const { locale, messages } = await getRequestI18n();
  return <StateView actionHref="/home" actionLabel={messages.returnHome} kind="empty" title={portalMessages[locale].marketplace} description={messages.globalErrorDescription} />;
}