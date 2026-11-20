'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { useRef, useState } from 'react';
import { versionTag, type PricingVersion } from '@/lib/pricing-admin-client';
import type { Simulation } from '@/lib/pricing-admin-types';
import { AuthorizeDialog } from './AuthorizeDialog';
import { SimulatorPanel } from './SimulatorPanel';
import { PricingMessage, usePricingCommand } from './usePricingCommand';

type Props = {
  version: PricingVersion;
  isFounder: boolean;
  onChanged: (version: PricingVersion) => void;
  onSimulated?: (simulation: Simulation) => void;
};

const simulatable = new Set(['DRAFT', 'SIMULATED']);
const discardable = new Set(['DRAFT', 'SIMULATED', 'SUBMITTED']);

export function DraftWorkflow({ version, isFounder, onChanged, onSimulated }: Props) {
  const { busy, message, run, setMessage } = usePricingCommand();
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [secondConfirmation, setSecondConfirmation] = useState(false);
  const [discardReason, setDiscardReason] = useState('');
  const [authorizing, setAuthorizing] = useState(false);
  const authorizeButton = useRef<HTMLButtonElement>(null);
  const guarded =
    version.needsSecondConfirmation ||
    (simulation?.warnings ?? []).some((warning) => warning.code === 'NEEDS_SECOND_CONFIRMATION');

  async function simulate() {
    const result = await run<Simulation>('POST', `drafts/${version.versionId}/simulate`, {
      schemaVersion: '1.0',
      expectedVersion: versionTag(version),
    });
    if (!result.ok) return;
    setSimulation(result.data);
    onSimulated?.(result.data);
    const refreshed = await run<PricingVersion>(
      'GET',
      `drafts/${version.versionId}`,
      undefined,
      'Simulation complete.'
    );
    if (refreshed.ok) onChanged(refreshed.data);
  }

  async function submit() {
    const result = await run<PricingVersion>(
      'POST',
      `drafts/${version.versionId}/submit`,
      { schemaVersion: '1.0', expectedVersion: versionTag(version), secondConfirmation: guarded && secondConfirmation },
      'Submitted for the Founder.'
    );
    if (result.ok) onChanged(result.data);
  }

  async function discard() {
    if (discardReason.trim() === '') {
      setMessage({ kind: 'error', text: 'Give a reason before discarding.' });
      return;
    }
    const result = await run<PricingVersion>(
      'POST',
      `drafts/${version.versionId}/discard`,
      { schemaVersion: '1.0', expectedVersion: versionTag(version), reason: discardReason.trim() },
      'Discarded.'
    );
    if (result.ok) onChanged(result.data);
  }

  async function activateForSale() {
    const result = await run<{ forSale: boolean }>(
      'POST',
      `packages/${version.versionId}/activate-for-sale`,
      { schemaVersion: '1.0', expectedVersion: versionTag(version) },
      'The package is now for sale.'
    );
    if (result.ok) onChanged(version);
  }

  return (
    <section aria-label={`Workflow for version ${version.versionNo}`} className="workbench-section">
      <h3>
        Version {version.versionNo} is {version.state.toLowerCase()}
      </h3>
      <div className="workbench-stack">
        {simulatable.has(version.state) ? (
          <button className="secondary-link" disabled={busy} onClick={() => void simulate()} type="button">
            Simulate
          </button>
        ) : null}
        {version.state === 'SIMULATED' ? (
          <>
            {guarded ? (
              <label>
                <input
                  checked={secondConfirmation}
                  onChange={(event) => setSecondConfirmation(event.target.checked)}
                  type="checkbox"
                />
                I confirm this large change a second time
              </label>
            ) : null}
            <button
              className="primary-command"
              disabled={busy || (guarded && !secondConfirmation)}
              onClick={() => void submit()}
              type="button"
            >
              Submit for authorization
            </button>
          </>
        ) : null}
        {version.state === 'SUBMITTED' ? (
          <>
            <button
              aria-describedby={isFounder ? undefined : `founder-only-${version.versionId}`}
              className="primary-command"
              disabled={!isFounder || busy}
              onClick={() => setAuthorizing(true)}
              ref={authorizeButton}
              type="button"
            >
              Authorize
            </button>
            {isFounder ? null : (
              <span className="workbench-hint" id={`founder-only-${version.versionId}`}>
                Only the Founder can authorize.
              </span>
            )}
          </>
        ) : null}
        {version.kind === 'PACKAGE' && version.state === 'EFFECTIVE' ? (
          <>
            <button
              aria-describedby={isFounder ? undefined : `sale-founder-only-${version.versionId}`}
              className="primary-command"
              disabled={!isFounder || busy}
              onClick={() => void activateForSale()}
              type="button"
            >
              Activate for sale
            </button>
            {isFounder ? null : (
              <span className="workbench-hint" id={`sale-founder-only-${version.versionId}`}>
                Only the Founder can put a package on sale.
              </span>
            )}
          </>
        ) : null}
      </div>
      {discardable.has(version.state) ? (
        <div className="workbench-form">
          <label htmlFor={`discard-${version.versionId}`}>Reason for discarding</label>
          <input
            id={`discard-${version.versionId}`}
            onChange={(event) => setDiscardReason(event.target.value)}
            type="text"
            value={discardReason}
          />
          <button className="secondary-link" disabled={busy} onClick={() => void discard()} type="button">
            Discard
          </button>
        </div>
      ) : null}
      <PricingMessage message={message} />
      <SimulatorPanel result={simulation} />
      {authorizing ? (
        <AuthorizeDialog
          isFounder={isFounder}
          onAuthorized={(authorized) => {
            setAuthorizing(false);
            onChanged(authorized);
          }}
          onClose={() => {
            setAuthorizing(false);
            queueMicrotask(() => authorizeButton.current?.focus());
          }}
          simulation={simulation}
          version={version}
        />
      ) : null}
    </section>
  );
}
