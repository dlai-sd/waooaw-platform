// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { PackageWorkspace } from '@/components/admin/pricing/PackageWorkspace';
import { PricingPageFrame } from '@/components/admin/pricing/PricingPageFrame';
import { loadCatalogue, loadVersions, requirePricingPage } from '@/lib/pricing-admin-pages';
import Link from 'next/link';

export default async function PackagesPage() {
  const { accessToken, isFounder } = await requirePricingPage();
  const packages = await loadVersions(accessToken, 'PACKAGE');
  const catalogue = await loadCatalogue(accessToken, packages ?? []);
  return (
    <PricingPageFrame
      current="/admin/pricing/packages"
      intro="Priced bundles of agent components. A package goes on sale only after the Founder authorizes it and every component is available."
      title="Packages"
    >
      {packages === null ? (
        <p className="workbench-message workbench-message-error" role="alert">
          <strong>Error:</strong> The pricing service could not be reached, so packages cannot be shown. Try again
          shortly.
        </p>
      ) : (
        <section aria-label="Package versions" className="workbench-section">
          <h2>Package versions</h2>
          {packages.length === 0 ? (
            <p className="workbench-hint">No packages yet. Create the first draft below.</p>
          ) : (
            <table aria-label="Package versions">
              <thead>
                <tr>
                  <th scope="col">Package</th>
                  <th scope="col">Description</th>
                  <th scope="col">Version</th>
                  <th scope="col">State</th>
                  <th scope="col">Open</th>
                </tr>
              </thead>
              <tbody>
                {packages.map((version) => (
                  <tr key={version.versionId}>
                    <th scope="row">{version.subjectKey}</th>
                    <td>{typeof version.body.description === 'string' ? version.body.description : ''}</td>
                    <td>{version.versionNo}</td>
                    <td>{version.state}</td>
                    <td>
                      <Link
                        aria-label={`Open ${version.subjectKey} version ${version.versionNo}`}
                        className="secondary-link"
                        href={`/admin/pricing/packages/${version.versionId}`}
                      >
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
      <section aria-label="New package draft" className="workbench-section">
        <h2>New package draft</h2>
        <PackageWorkspace catalogue={catalogue} isFounder={isFounder} version={null} />
      </section>
    </PricingPageFrame>
  );
}
