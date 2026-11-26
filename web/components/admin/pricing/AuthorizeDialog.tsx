'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { useEffect, useId, useRef, useState } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import { versionTag, type PricingVersion } from '@/lib/pricing-admin-client';
import type { Simulation } from '@/lib/pricing-admin-types';
import { stepUpSignedInText, useResumeAfterStepUp } from '@/lib/step-up-resume';
import { SimulatorPanel } from './SimulatorPanel';
import { PricingMessage, usePricingCommand } from './usePricingCommand';

type Props = {
  version: PricingVersion;
  simulation: Simulation | null;
  isFounder: boolean;
  onClose: () => void;
  onAuthorized: (version: PricingVersion) => void;
};

const saleGateCodes = new Set(['PACKAGE_COMPONENT_NOT_AVAILABLE']);

export function AuthorizeDialog({ version, simulation, isFounder, onClose, onAuthorized }: Props) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  const { busy, message, run } = usePricingCommand();
  const [confirmed, setConfirmed] = useState(false);
  const [effectiveFrom, setEffectiveFrom] = useState('');
  const [stepUp, setStepUp] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const authorizeKey = `pricing.authorize.${version.versionId}`;

  // Authorizing puts a price on sale, so after the step-up only the date comes back; the person presses Authorize and
  // gives any second confirmation again.
  useResumeAfterStepUp<{ effectiveFrom?: unknown }>(authorizeKey, (payload) => {
    if (typeof payload.effectiveFrom === 'string') setEffectiveFrom(payload.effectiveFrom);
    setSignedIn(true);
  });

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  const warnings = simulation?.warnings ?? [];
  const guarded =
    version.needsSecondConfirmation || warnings.some((warning) => warning.code === 'NEEDS_SECOND_CONFIRMATION');
  const saleGates = warnings.filter((warning) => saleGateCodes.has(warning.code));
  const canAuthorize = isFounder && (!guarded || confirmed) && !busy;

  async function authorize() {
    setSignedIn(false);
    const body: Record<string, unknown> = {
      schemaVersion: '1.0',
      expectedVersion: versionTag(version),
      secondConfirmation: guarded && confirmed,
    };
    if (effectiveFrom.trim() !== '') body.effectiveFrom = new Date(`${effectiveFrom}Z`).toISOString();
    const result = await run<PricingVersion>('POST', `drafts/${version.versionId}/authorize`, body, 'Authorized.');
    if (result.ok) onAuthorized(result.data);
    else setStepUp(result.problem.code === 'PRICING_STEP_UP_REQUIRED');
  }

  return (
    <dialog
      aria-labelledby={titleId}
      aria-modal="true"
      className="workbench-section"
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose();
      }}
      open
    >
      <h2 id={titleId}>
        Authorize {version.kind.toLowerCase()} {version.subjectKey}
      </h2>
      {isFounder ? null : (
        <p className="workbench-hint" role="note">
          Only the Founder can authorize a pricing version.
        </p>
      )}
      <SimulatorPanel result={simulation} />
      {simulation === null ? (
        <p className="workbench-hint">Run the simulation first so the floor, margin and differences are shown here.</p>
      ) : null}
      {saleGates.length > 0 ? (
        <ul aria-label="Gates before sale" className="workbench-plain-list">
          {saleGates.map((warning) => (
            <li key={`${warning.code}:${warning.componentId ?? ''}`}>
              <strong>Cannot go on sale yet:</strong> {warning.message}
            </li>
          ))}
        </ul>
      ) : null}
      <div className="workbench-form">
        <label>
          Effective from (UTC, optional)
          <input
            disabled={!isFounder}
            onChange={(event) => setEffectiveFrom(event.target.value)}
            type="datetime-local"
            value={effectiveFrom}
          />
        </label>
        {guarded ? (
          <label>
            <input
              checked={confirmed}
              disabled={!isFounder}
              onChange={(event) => setConfirmed(event.target.checked)}
              type="checkbox"
            />
            I confirm this large change a second time
          </label>
        ) : null}
      </div>
      {signedIn ? <output className="workbench-hint">{stepUpSignedInText('Authorize')}</output> : null}
      <PricingMessage message={message} />
      {stepUp ? (
        <StepUpCommand payload={{ versionId: version.versionId, effectiveFrom }} pendingKey={authorizeKey} />
      ) : null}
      <p>
        <button className="primary-command" disabled={!canAuthorize} onClick={() => void authorize()} type="button">
          Authorize
        </button>{' '}
        <button className="secondary-link" onClick={onClose} ref={closeRef} type="button">
          Close
        </button>
      </p>
    </dialog>
  );
}
