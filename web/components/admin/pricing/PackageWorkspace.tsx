'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import type { PricingVersion } from '@/lib/pricing-admin-client';
import type { PackageCatalogue, Simulation } from '@/lib/pricing-admin-types';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Breadcrumb } from '@/components/admin/master-detail/Breadcrumb';
import { StateStrip } from '@/components/admin/master-detail/StateStrip';
import { DraftWorkflow } from './DraftWorkflow';
import { PackageEditor, type PackageTab } from './PackageEditor';

type Props = {
  version: PricingVersion | null;
  // The version a new draft starts from; the new draft is still a blank record until it is saved.
  seed?: PricingVersion | null;
  catalogue: PackageCatalogue;
  isFounder: boolean;
};

const tabs: Array<{ id: PackageTab; label: string }> = [
  { id: 'details', label: 'Details' },
  { id: 'components', label: 'Components' },
  { id: 'review', label: 'Review and sale' },
];
const editable = new Set(['DRAFT', 'SIMULATED']);

// One package on its own page: Details, then its Components (each on a page of its own), then Review and sale.
export function PackageWorkspace({ version: initial, seed = null, catalogue, isFounder }: Props) {
  const router = useRouter();
  const [version, setVersion] = useState(initial);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [tab, setTab] = useState<PackageTab>('details');

  const saved = (next: PricingVersion) => {
    const created = version === null;
    setVersion(next);
    // A simulation describes the draft as it was; after a save it would show numbers the saved draft no longer has.
    setSimulation(null);
    if (created) router.replace(`/admin/pricing/packages/${next.versionId}`);
  };

  const heading =
    version === null
      ? 'New package'
      : `${typeof version.body.displayName === 'string' && version.body.displayName ? version.body.displayName : version.subjectKey} · version ${version.versionNo}`;

  return (
    <div className="workbench-stack">
      <Breadcrumb
        trail={[
          { label: 'Packages', href: '/admin/pricing/packages' },
          { label: version === null ? 'New package' : version.subjectKey },
        ]}
      />
      <section aria-label="Package header" className="workbench-section">
        <div className="master-detail-heading">
          <h2>{heading}</h2>
          {version !== null && !editable.has(version.state) ? (
            <button
              className="secondary-link"
              onClick={() => router.push(`/admin/pricing/packages/new?from=${version.versionId}`)}
              type="button"
            >
              New version from this
            </button>
          ) : null}
        </div>
        {version ? <StateStrip finalLabel="On sale" state={version.state} /> : null}
        {version === null && seed ? (
          <p className="workbench-hint">
            Starting from version {seed.versionNo} of {seed.subjectKey}. Nothing is saved until you create the draft.
          </p>
        ) : null}
        <div aria-label="Package sections" className="operations-tabs" role="tablist">
          {tabs.map((item) => (
            <button
              aria-selected={tab === item.id}
              className={tab === item.id ? 'primary-command' : 'secondary-link'}
              id={`package-tab-${item.id}`}
              key={item.id}
              onClick={() => setTab(item.id)}
              role="tab"
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>
      <div aria-labelledby={`package-tab-${tab}`} role="tabpanel">
        <PackageEditor
          catalogue={catalogue}
          draft={version}
          key={version?.versionId ?? 'new'}
          onSaved={saved}
          seed={seed}
          simulation={simulation}
          tab={tab}
        />
        {version && tab === 'review' ? (
          <DraftWorkflow
            isFounder={isFounder}
            key={`workflow:${version.versionId}`}
            onChanged={setVersion}
            onSimulated={setSimulation}
            version={version}
          />
        ) : null}
      </div>
    </div>
  );
}
