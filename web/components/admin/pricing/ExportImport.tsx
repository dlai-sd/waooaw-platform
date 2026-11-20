'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-06
// Constitutional basis: C-023, C-059, C-063, C-088

import { useState, type ChangeEvent } from 'react';
import { problemText } from '@/lib/pricing-admin-client';
import { PricingMessage, usePricingCommand } from './usePricingCommand';

type ImportResult = {
  created: { kind: string; subjectKey: string; versionId: string; state: string }[];
  rejected: { kind: string; subjectKey: string; code: string; message: string }[];
};

export function ExportImport() {
  const exporting = usePricingCommand();
  const importing = usePricingCommand();
  const [bundleText, setBundleText] = useState('');
  const [downloadText, setDownloadText] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<ImportResult | null>(null);

  async function exportBundle() {
    const result = await exporting.run<unknown>('GET', 'versions/export', undefined, 'Bundle exported.');
    setDownloadText(result.ok ? JSON.stringify(result.data, null, 2) : null);
  }

  async function importBundle() {
    setOutcome(null);
    let bundle: unknown;
    try {
      bundle = JSON.parse(bundleText);
    } catch {
      importing.setMessage({ kind: 'error', text: 'The bundle is not valid JSON.' });
      return;
    }
    const result = await importing.run<ImportResult>('POST', 'versions/import', { schemaVersion: '1.0', bundle });
    if (!result.ok) return;
    setOutcome(result.data);
    const created = result.data.created.length;
    const rejected = result.data.rejected.length;
    importing.setMessage({
      kind: rejected > 0 && created === 0 ? 'error' : 'success',
      text: `${created} drafts created, ${rejected} entries rejected. Imported entries are drafts that the Founder still has to authorize.`,
    });
  }

  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) setBundleText(await file.text());
  }

  return (
    <section aria-label="Export and import" className="workbench-section">
      <h2>Export and import</h2>
      <div className="workbench-stack">
        <h3>Export</h3>
        <p className="workbench-hint">
          A signed bundle of every effective and authorized version, for recovery after a reset.
        </p>
        <button className="secondary-link" disabled={exporting.busy} onClick={() => void exportBundle()} type="button">
          Export versions
        </button>
        <PricingMessage message={exporting.message} />
        {downloadText ? (
          <>
            <a
              download="pricing-versions.json"
              href={`data:application/json;charset=utf-8,${encodeURIComponent(downloadText)}`}
            >
              Download bundle
            </a>
            <label htmlFor="export-bundle">Exported bundle</label>
            <textarea id="export-bundle" readOnly rows={6} value={downloadText} />
          </>
        ) : null}
      </div>
      <div className="workbench-form">
        <h3>Import</h3>
        <p className="workbench-hint">
          Every entry is checked by the same rules and created as a draft. Nothing becomes effective until the Founder
          authorizes it.
        </p>
        <label htmlFor="import-file">Bundle file</label>
        <input
          accept="application/json,.json"
          id="import-file"
          onChange={(event) => void chooseFile(event)}
          type="file"
        />
        <label htmlFor="import-bundle">Bundle contents</label>
        <textarea
          id="import-bundle"
          onChange={(event) => setBundleText(event.target.value)}
          rows={6}
          value={bundleText}
        />
        <button
          className="secondary-link"
          disabled={importing.busy || bundleText.trim() === ''}
          onClick={() => void importBundle()}
          type="button"
        >
          Import as drafts
        </button>
        <PricingMessage message={importing.message} />
        {outcome && outcome.created.length > 0 ? (
          <ul aria-label="Created drafts" className="workbench-plain-list">
            {outcome.created.map((entry) => (
              <li key={entry.versionId}>
                {entry.kind} {entry.subjectKey}: {entry.state.toLowerCase()}
              </li>
            ))}
          </ul>
        ) : null}
        {outcome && outcome.rejected.length > 0 ? (
          <ul aria-label="Rejected entries" className="workbench-plain-list">
            {outcome.rejected.map((entry) => (
              <li key={`${entry.kind}:${entry.subjectKey}`}>
                {entry.kind} {entry.subjectKey}: {problemText({ code: entry.code })} {entry.message}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}
