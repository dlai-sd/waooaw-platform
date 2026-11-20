// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { KindWorkspace } from '@/components/admin/pricing/KindWorkspace';
import { PricingPageFrame } from '@/components/admin/pricing/PricingPageFrame';
import type { PricingKind } from '@/lib/pricing-admin-client';
import { loadVersions, requirePricingPage } from '@/lib/pricing-admin-pages';
import type { FormKind } from '@/lib/pricing-forms';

type Props = { kind: FormKind & PricingKind; current: string; title: string; intro: string; notice?: string };

export async function KindPage({ kind, current, title, intro, notice }: Props) {
  const { accessToken, isFounder } = await requirePricingPage();
  const versions = await loadVersions(accessToken, kind);
  return (
    <PricingPageFrame current={current} intro={intro} title={title}>
      {notice ? <p className="workbench-hint">{notice}</p> : null}
      {versions === null ? (
        <p className="workbench-message workbench-message-error" role="alert">
          <strong>Error:</strong> The pricing service could not be reached, so versions cannot be shown or changed. Try
          again shortly.
        </p>
      ) : (
        <KindWorkspace isFounder={isFounder} kind={kind} versions={versions} />
      )}
    </PricingPageFrame>
  );
}
