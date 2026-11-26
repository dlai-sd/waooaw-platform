// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { PackageWorkspace } from '@/components/admin/pricing/PackageWorkspace';
import { PricingPageFrame } from '@/components/admin/pricing/PricingPageFrame';
import { loadCatalogue, loadVersion, loadVersions, requirePricingPage } from '@/lib/pricing-admin-pages';

type Props = { searchParams: Promise<{ from?: string }> };

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// A blank draft, or one that starts from the values of an existing version (?from=...). Nothing exists until it is saved.
export default async function NewPackagePage({ searchParams }: Props) {
  const { from } = await searchParams;
  const { accessToken, isFounder } = await requirePricingPage();
  const source = from && uuid.test(from) ? await loadVersion(accessToken, from) : null;
  const seed = source?.kind === 'PACKAGE' ? source : null;
  const packages = await loadVersions(accessToken, 'PACKAGE');
  const catalogue = await loadCatalogue(accessToken, packages ?? []);
  return (
    <PricingPageFrame
      current="/admin/pricing/packages"
      intro="Fill in the details, then its components, then review what stops it going on sale."
      title="New package"
    >
      <PackageWorkspace catalogue={catalogue} isFounder={isFounder} seed={seed} version={null} />
    </PricingPageFrame>
  );
}
