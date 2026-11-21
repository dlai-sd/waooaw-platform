// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { notFound } from 'next/navigation';
import { PackageWorkspace } from '@/components/admin/pricing/PackageWorkspace';
import { PricingPageFrame } from '@/components/admin/pricing/PricingPageFrame';
import { loadCatalogue, loadVersion, requirePricingPage } from '@/lib/pricing-admin-pages';

type Props = { params: Promise<{ draftId: string }> };

export default async function PackageDraftPage({ params }: Props) {
  const { draftId } = await params;
  const { accessToken, isFounder } = await requirePricingPage();
  const version = await loadVersion(accessToken, draftId);
  if (!version || version.kind !== 'PACKAGE') notFound();
  const catalogue = await loadCatalogue(accessToken, [version]);
  return (
    <PricingPageFrame
      current="/admin/pricing/packages"
      intro={`${version.subjectKey}, version ${version.versionNo}, state ${version.state}.`}
      title="Package"
    >
      <PackageWorkspace catalogue={catalogue} isFounder={isFounder} version={version} />
    </PricingPageFrame>
  );
}
