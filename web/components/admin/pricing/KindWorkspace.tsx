'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { useState } from 'react';
import type { PricingVersion } from '@/lib/pricing-admin-client';
import { formSpecs, valuesFromBody, type FormKind } from '@/lib/pricing-forms';
import { Breadcrumb } from '@/components/admin/master-detail/Breadcrumb';
import { StateStrip } from '@/components/admin/master-detail/StateStrip';
import { DraftForm } from './DraftForm';
import { DraftWorkflow } from './DraftWorkflow';

type Props = { kind: FormKind; versions: PricingVersion[]; isFounder: boolean };
type View = { mode: 'list' } | { mode: 'new'; seed?: Record<string, unknown> } | { mode: 'detail'; id: string };

const editable = new Set(['DRAFT', 'SIMULATED']);

// The list of subjects and versions, then one version on its own page; a draft is created only on request.
export function KindWorkspace({ kind, versions: initial, isFounder }: Props) {
  const spec = formSpecs[kind];
  const [versions, setVersions] = useState(initial);
  const [view, setView] = useState<View>({ mode: 'list' });
  const selected = view.mode === 'detail' ? (versions.find((version) => version.versionId === view.id) ?? null) : null;

  const upsert = (version: PricingVersion) => {
    setVersions((current) =>
      current.some((item) => item.versionId === version.versionId)
        ? current.map((item) => (item.versionId === version.versionId ? version : item))
        : [version, ...current]
    );
    setView({ mode: 'detail', id: version.versionId });
  };
  const toList = () => setView({ mode: 'list' });

  if (view.mode === 'new') {
    return (
      <div className="workbench-stack">
        <Breadcrumb trail={[{ label: spec.title, onSelect: toList }, { label: 'New draft' }]} />
        <DraftForm draft={null} key="form:new" onSaved={upsert} seedBody={view.seed} spec={spec} />
      </div>
    );
  }

  if (selected) {
    const isEditable = editable.has(selected.state);
    const values = valuesFromBody(spec, selected.body);
    return (
      <div className="workbench-stack">
        <Breadcrumb
          trail={[
            { label: spec.title, onSelect: toList },
            { label: `${selected.subjectKey} version ${selected.versionNo}` },
          ]}
        />
        <section aria-label={`${selected.subjectKey} version ${selected.versionNo}`} className="workbench-section">
          <div className="master-detail-heading">
            <h2>
              {selected.subjectKey}
              {selected.seed ? ' (seed)' : ''} · version {selected.versionNo}
            </h2>
            {isEditable ? null : (
              <button
                className="secondary-link"
                onClick={() => setView({ mode: 'new', seed: selected.body })}
                type="button"
              >
                New version from this
              </button>
            )}
          </div>
          <StateStrip state={selected.state} />
        </section>
        {isEditable ? (
          <DraftForm draft={selected} key={`form:${selected.versionId}`} onSaved={upsert} spec={spec} />
        ) : (
          <section aria-label="Values" className="workbench-section">
            <h3>Values (read only)</h3>
            <dl className="detail-list">
              {spec.fields.map((field) => (
                <div key={field.name}>
                  <dt>{field.label}</dt>
                  <dd>{values[field.name] || 'not set'}</dd>
                </div>
              ))}
              <div>
                <dt>Effective from</dt>
                <dd>{selected.effectiveFrom ?? 'not set'}</dd>
              </div>
            </dl>
            <p className="workbench-hint">
              A version that has been submitted or authorized is never edited. Start a new version to change it.
            </p>
          </section>
        )}
        <DraftWorkflow
          isFounder={isFounder}
          key={`workflow:${selected.versionId}`}
          onChanged={upsert}
          version={selected}
        />
      </div>
    );
  }

  return (
    <div className="workbench-stack">
      <section aria-label={`${spec.title} versions`} className="workbench-section">
        <div className="master-detail-heading">
          <h2>Versions</h2>
          <button className="primary-command" onClick={() => setView({ mode: 'new' })} type="button">
            New draft
          </button>
        </div>
        {versions.length === 0 ? (
          <p className="workbench-hint">No versions yet. Choose “New draft” to create the first one.</p>
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
                <tr key={version.versionId}>
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
                      onClick={() => setView({ mode: 'detail', id: version.versionId })}
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
      </section>
    </div>
  );
}
