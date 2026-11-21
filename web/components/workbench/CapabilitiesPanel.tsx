'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { labelFor, plainWords } from '@/lib/workbench-i18n';
import { CommandMessage, useWorkbenchCommand, type WorkbenchPanelProps } from './useWorkbenchCommand';

export function CapabilitiesPanel(panel: WorkbenchPanelProps) {
  const { copy, snapshot } = panel;
  const command = useWorkbenchCommand(panel.relationshipId, copy, panel.onChanged);
  const items = snapshot.capabilities?.items ?? [];
  const change = snapshot.projection.availableCommands.find((item) => item.commandId === 'change_capability');
  const allowed = change?.enabled ?? false;
  const labels = new Map(
    (snapshot.wallet?.components ?? []).map((component) => [component.componentId, component.label])
  );

  function send(skillId: string, name: 'ENABLE' | 'PAUSE' | 'RESUME') {
    return command.run(`/capabilities/${encodeURIComponent(skillId)}/commands`, {
      schemaVersion: '1.0',
      expectedVersion: snapshot.version,
      command: name,
    });
  }

  return (
    <section aria-labelledby="workbench-capabilities-title" className="workbench-section">
      <h3 id="workbench-capabilities-title">{copy.capabilities}</h3>
      {snapshot.capabilities === null ? <p>{copy.problems.WORKBENCH_UNAVAILABLE}</p> : null}
      {snapshot.capabilities !== null && items.length === 0 ? <p>{copy.noCapabilities}</p> : null}
      {!allowed && change?.disabledReason ? <p className="workbench-hint">{change.disabledReason}</p> : null}
      <ul className="workbench-cards">
        {items.map((item) => {
          const usable = allowed && item.availability !== 'UNAVAILABLE' && !command.busy;
          return (
            <li className="workbench-card" key={item.skillId}>
              <h4>{item.label}</h4>
              <p>
                {labelFor(copy.capabilityStates, item.state)} · {labelFor(copy.capabilityStates, item.availability)}
              </p>
              <p>
                {copy.approvalMode}: {plainWords(item.approvalMode)}
              </p>
              {item.nextRunMeaning ? (
                <p>
                  {copy.nextRun}: {item.nextRunMeaning}
                </p>
              ) : null}
              {item.componentIds.length > 0 ? (
                <p>
                  {copy.allowanceUsed}: {item.componentIds.map((id) => labels.get(id) ?? plainWords(id)).join(', ')}
                </p>
              ) : null}
              {item.limitation ? <p className="workbench-hint">{item.limitation}</p> : null}
              {item.state === 'NOT_ENABLED' ? (
                <button
                  className="primary-command"
                  disabled={!usable}
                  onClick={() => send(item.skillId, 'ENABLE')}
                  type="button"
                >
                  {copy.enable}
                  <span className="visually-hidden"> {item.label}</span>
                </button>
              ) : null}
              {item.state === 'ACTIVE' ? (
                <button
                  className="secondary-link"
                  disabled={!usable}
                  onClick={() => send(item.skillId, 'PAUSE')}
                  type="button"
                >
                  {copy.pause}
                  <span className="visually-hidden"> {item.label}</span>
                </button>
              ) : null}
              {item.state === 'PAUSED' ? (
                <button
                  className="primary-command"
                  disabled={!usable}
                  onClick={() => send(item.skillId, 'RESUME')}
                  type="button"
                >
                  {copy.resume}
                  <span className="visually-hidden"> {item.label}</span>
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>
      <CommandMessage message={command.message} />
    </section>
  );
}
