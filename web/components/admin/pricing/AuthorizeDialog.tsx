'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { signIn } from 'next-auth/react';
import { useEffect, useId, useRef, useState } from 'react';
import { versionTag, type PricingVersion } from '@/lib/pricing-admin-client';
import type { Simulation } from '@/lib/pricing-admin-types';
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

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  const warnings = simulation?.warnings ?? [];
  const guarded =
    version.needsSecondConfirmation || warnings.some((warning) => warning.code === 'NEEDS_SECOND_CONFIRMATION');
  const saleGates = warnings.filter((warning) => saleGateCodes.has(warning.code));
  const canAuthorize = isFounder && (!guarded || confirmed) && !busy;

  async function authorize() {
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
      <PricingMessage message={message} />
      {stepUp ? (
        <p>
          <button
            className="secondary-link"
            onClick={() =>
              void signIn(
                'keycloak',
                { callbackUrl: window.location.href, waooawIntent: 'LOGIN' },
                { prompt: 'login', max_age: '0', acr_values: '2' }
              )
            }
            type="button"
          >
            Confirm with multi-factor sign-in
          </button>
        </p>
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
