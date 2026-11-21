'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-023, C-042, C-059, C-063, ADR-051

import { useEffect, useRef, useState } from 'react';
import { CommandMessage, useWorkbenchCommand, type WorkbenchPanelProps } from './useWorkbenchCommand';

// Stop is offered in every composition and is never disabled by the allowance or by the plan.
export function ControlsBar(panel: WorkbenchPanelProps) {
  const { copy, snapshot } = panel;
  const command = useWorkbenchCommand(panel.relationshipId, copy, panel.onChanged);
  const [confirming, setConfirming] = useState(false);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const stopRef = useRef<HTMLButtonElement>(null);
  const pause = snapshot.projection.availableCommands.find((item) => item.commandId === 'pause');

  useEffect(() => {
    if (confirming) confirmRef.current?.focus();
  }, [confirming]);

  function cancel() {
    setConfirming(false);
    stopRef.current?.focus();
  }

  async function stop() {
    await command.run('/controls/stop', { schemaVersion: '1.0', expectedVersion: snapshot.version });
    setConfirming(false);
  }

  return (
    <section aria-label={copy.controls} className="workbench-controls">
      <fieldset className="workbench-actions" aria-label={copy.controls}>
        <button
          className="secondary-link"
          disabled={command.busy || (pause ? !pause.enabled : false)}
          onClick={() => command.run('/controls/pause', { schemaVersion: '1.0', expectedVersion: snapshot.version })}
          type="button"
        >
          {copy.pauseWork}
        </button>
        <button
          aria-expanded={confirming}
          className="workbench-stop"
          disabled={command.busy}
          onClick={() => setConfirming(true)}
          ref={stopRef}
          type="button"
        >
          {copy.stop}
        </button>
      </fieldset>
      {confirming ? (
        <fieldset
          className="workbench-actions"
          onKeyDown={(event) => {
            if (event.key === 'Escape') cancel();
          }}
          aria-label={copy.stopConfirm}
        >
          <button className="workbench-stop" disabled={command.busy} onClick={stop} ref={confirmRef} type="button">
            {copy.stopConfirm}
          </button>
          <button className="secondary-link" onClick={cancel} type="button">
            {copy.cancel}
          </button>
        </fieldset>
      ) : null}
      <CommandMessage message={command.message} />
    </section>
  );
}
