'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { useState } from 'react';
import type { PricingVersion } from '@/lib/pricing-admin-client';
import { formSpecs, type FormKind } from '@/lib/pricing-forms';
import { DraftForm } from './DraftForm';
import { DraftWorkflow } from './DraftWorkflow';

type Props = { kind: FormKind; versions: PricingVersion[]; isFounder: boolean };

export function KindWorkspace({ kind, versions: initial, isFounder }: Props) {
  const spec = formSpecs[kind];
  const [versions, setVersions] = useState(initial);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = versions.find((version) => version.versionId === selectedId) ?? null;

  const upsert = (version: PricingVersion) => {
    setVersions((current) =>
      current.some((item) => item.versionId === version.versionId)
        ? current.map((item) => (item.versionId === version.versionId ? version : item))
        : [version, ...current]
    );
    setSelectedId(version.versionId);
  };

  return (
    <div className="workbench-stack">
      <section aria-label={`${spec.title} versions`} className="workbench-section">
        <h2>Versions</h2>
        {versions.length === 0 ? (
          <p className="workbench-hint">No versions yet. Create the first draft below.</p>
        ) : (
          <table aria-label={`${spec.title} versions`}>
            <thead>
              <tr>
                <th scope="col">Subject</th>
                <th scope="col">Version</th>
                <th scope="col">State</th>
                <th scope="col">Effective from</th>
                <th scope="col">Open</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((version) => (
                <tr aria-current={version.versionId === selectedId ? 'true' : undefined} key={version.versionId}>
                  <th scope="row">
                    {version.subjectKey}
                    {version.seed ? ' (seed)' : ''}
                  </th>
                  <td>{version.versionNo}</td>
                  <td>{version.state}</td>
                  <td>{version.effectiveFrom ?? 'not set'}</td>
                  <td>
                    <button
                      aria-label={`Open ${version.subjectKey} version ${version.versionNo}`}
                      className="secondary-link"
                      onClick={() => setSelectedId(version.versionId)}
                      type="button"
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {selected ? (
          <button className="secondary-link" onClick={() => setSelectedId(null)} type="button">
            Start a blank draft
          </button>
        ) : null}
      </section>
      <DraftForm draft={selected} key={`form:${selectedId ?? 'new'}`} onSaved={upsert} spec={spec} />
      {selected ? (
        <DraftWorkflow
          isFounder={isFounder}
          key={`workflow:${selected.versionId}`}
          onChanged={upsert}
          version={selected}
        />
      ) : null}
    </div>
  );
}
