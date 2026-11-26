// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { PricingPageFrame } from '@/components/admin/pricing/PricingPageFrame';
import { loadVersions, requirePricingPage } from '@/lib/pricing-admin-pages';
import Link from 'next/link';

export default async function PackagesPage() {
  const { accessToken } = await requirePricingPage();
  const packages = await loadVersions(accessToken, 'PACKAGE');
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
          <div className="master-detail-heading">
            <h2>Package versions</h2>
            <Link className="primary-command" href="/admin/pricing/packages/new">
              New package
            </Link>
          </div>
          {packages.length === 0 ? (
            <p className="workbench-hint">No packages yet. Choose “New package” to create the first one.</p>
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
    </PricingPageFrame>
  );
}
