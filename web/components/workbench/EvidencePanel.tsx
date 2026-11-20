'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { labelFor, plainWords } from '@/lib/workbench-i18n';
import { CommandMessage, useWorkbenchCommand, type WorkbenchPanelProps } from './useWorkbenchCommand';

export function EvidencePanel(panel: WorkbenchPanelProps) {
  const { copy, snapshot } = panel;
  const command = useWorkbenchCommand(panel.relationshipId, copy, panel.onChanged);
  const items = snapshot.evidence?.items ?? [];
  const exportCommand = snapshot.projection.availableCommands.find((item) => item.commandId === 'export_evidence');
  const allowed = exportCommand?.enabled ?? false;

  function requestExport(format: 'PDF' | 'JSON') {
    return command.run(
      '/evidence/exports',
      { schemaVersion: '1.0', expectedVersion: snapshot.version, scope: 'RELATIONSHIP', format },
      copy.exportRequested
    );
  }

  return (
    <section aria-labelledby="workbench-evidence-title" className="workbench-section">
      <h3 id="workbench-evidence-title">{copy.evidence}</h3>
      <p className="workbench-hint">
        {copy.evidenceState}:{' '}
        {labelFor(copy.evidenceStates, snapshot.evidence?.evidenceState ?? snapshot.projection.evidenceState)}
      </p>
      {snapshot.evidence === null ? <p>{copy.problems.WORKBENCH_UNAVAILABLE}</p> : null}
      {snapshot.evidence !== null && items.length === 0 ? <p>{copy.noEvidence}</p> : null}
      <ul className="workbench-plain-list">
        {items.map((item) => (
          <li key={item.evidenceRef}>
            <strong>{plainWords(item.kind)}</strong> {item.summary} · {item.producedAt.slice(0, 10)} ·{' '}
            {labelFor(copy.freshnessStates, item.freshness)}
          </li>
        ))}
      </ul>
      {!allowed && exportCommand?.disabledReason ? (
        <p className="workbench-hint">{exportCommand.disabledReason}</p>
      ) : null}
      <fieldset className="workbench-actions" aria-label={copy.exportEvidence}>
        <button
          className="secondary-link"
          disabled={!allowed || command.busy}
          onClick={() => requestExport('PDF')}
          type="button"
        >
          {copy.exportEvidence} (PDF)
        </button>
        <button
          className="secondary-link"
          disabled={!allowed || command.busy}
          onClick={() => requestExport('JSON')}
          type="button"
        >
          {copy.exportEvidence} (JSON)
        </button>
      </fieldset>
      <CommandMessage message={command.message} />
    </section>
  );
}
