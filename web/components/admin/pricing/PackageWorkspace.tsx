'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import type { PricingVersion } from '@/lib/pricing-admin-client';
import type { PackageCatalogue, Simulation } from '@/lib/pricing-admin-types';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { DraftWorkflow } from './DraftWorkflow';
import { PackageEditor } from './PackageEditor';

type Props = { version: PricingVersion | null; catalogue: PackageCatalogue; isFounder: boolean };

export function PackageWorkspace({ version: initial, catalogue, isFounder }: Props) {
  const router = useRouter();
  const [version, setVersion] = useState(initial);
  const [simulation, setSimulation] = useState<Simulation | null>(null);

  const saved = (next: PricingVersion) => {
    const created = version === null;
    setVersion(next);
    // A simulation describes the draft as it was; after a save it would show numbers the saved draft no longer has.
    setSimulation(null);
    if (created) router.replace(`/admin/pricing/packages/${next.versionId}`);
  };

  return (
    <div className="workbench-stack">
      <PackageEditor
        catalogue={catalogue}
        draft={version}
        key={version?.versionId ?? 'new'}
        onSaved={saved}
        simulation={simulation}
      />
      {version ? (
        <DraftWorkflow
          isFounder={isFounder}
          key={version.versionId}
          onChanged={setVersion}
          onSimulated={setSimulation}
          version={version}
        />
      ) : null}
    </div>
  );
}
