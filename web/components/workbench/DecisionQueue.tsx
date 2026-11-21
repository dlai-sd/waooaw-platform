'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { labelFor } from '@/lib/workbench-i18n';
import { CommandMessage, useWorkbenchCommand, type WorkbenchPanelProps } from './useWorkbenchCommand';

type Resolution = 'APPROVE' | 'DECLINE' | 'DEFER';

export function DecisionQueue(panel: WorkbenchPanelProps) {
  const { copy, snapshot } = panel;
  const command = useWorkbenchCommand(panel.relationshipId, copy, panel.onChanged);
  const { decisions, availableCommands } = snapshot.projection;
  const resolve = availableCommands.find((item) => item.commandId === 'resolve_decision');
  const allowed = resolve?.enabled ?? false;

  function send(decisionId: string, version: string, resolution: Resolution) {
    return command.run(`/decisions/${encodeURIComponent(decisionId)}/resolve`, {
      schemaVersion: '1.0',
      expectedVersion: version,
      resolution,
    });
  }

  return (
    <section aria-labelledby="workbench-decisions-title" className="workbench-section">
      <h3 id="workbench-decisions-title">{copy.decisions}</h3>
      {decisions.length === 0 ? <p>{copy.noDecisions}</p> : null}
      {!allowed && decisions.length > 0 && resolve?.disabledReason ? (
        <p className="workbench-hint">{resolve.disabledReason}</p>
      ) : null}
      <ul className="workbench-cards">
        {decisions.map((decision) => (
          <li className="workbench-card" key={decision.decisionId}>
            <p>
              <strong>{decision.effect}</strong>
            </p>
            <dl className="workbench-facts">
              <div>
                <dt>{copy.decidedBy}</dt>
                <dd>{decision.authority}</dd>
              </div>
              {decision.cost ? (
                <div>
                  <dt>{copy.cost}</dt>
                  <dd>{decision.cost}</dd>
                </div>
              ) : null}
              {decision.expiresAt ? (
                <div>
                  <dt>{copy.expires}</dt>
                  <dd>{decision.expiresAt.slice(0, 10)}</dd>
                </div>
              ) : null}
              <div>
                <dt>{copy.freshness}</dt>
                <dd>{labelFor(copy.freshnessStates, decision.freshness)}</dd>
              </div>
            </dl>
            <fieldset className="workbench-actions" aria-label={decision.effect}>
              <button
                className="primary-command"
                disabled={!allowed || command.busy}
                onClick={() => send(decision.decisionId, decision.version, 'APPROVE')}
                type="button"
              >
                {decision.confirmLabel}
              </button>
              <button
                className="secondary-link"
                disabled={!allowed || command.busy}
                onClick={() => send(decision.decisionId, decision.version, 'DECLINE')}
                type="button"
              >
                {decision.cancelLabel}
              </button>
              <button
                className="secondary-link"
                disabled={!allowed || command.busy}
                onClick={() => send(decision.decisionId, decision.version, 'DEFER')}
                type="button"
              >
                {copy.defer}
              </button>
            </fieldset>
          </li>
        ))}
      </ul>
      <CommandMessage message={command.message} />
    </section>
  );
}
