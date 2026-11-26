'use client';

// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R004, WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { useEffect, useId, useRef, useState } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import { PricingMessage, type PricingNotice } from '@/components/admin/pricing/usePricingCommand';
import { providerCall } from '@/lib/provider-admin-call';
import {
  outcomeLabel,
  problemText,
  type CredentialVersion,
  type ProviderSummary,
  type SavedVersion,
} from '@/lib/provider-admin-client';
import { stepUpSignedInText, useResumeAfterStepUp } from '@/lib/step-up-resume';

export type HistoryState =
  | { kind: 'loading' }
  | { kind: 'error'; text: string }
  | { kind: 'ready'; versions: CredentialVersion[] };

type Props = {
  provider: ProviderSummary;
  history: HistoryState;
  onReload: () => void;
  onRolledBack: (version: SavedVersion) => void;
};

function formatWhen(value: string | null): string {
  if (!value) return 'Not activated';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown' : `${date.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
}

function RollbackDialog({
  provider,
  version,
  signedIn,
  onClose,
  onRolledBack,
}: {
  provider: ProviderSummary;
  version: CredentialVersion;
  signedIn: boolean;
  onClose: () => void;
  onRolledBack: (version: SavedVersion) => void;
}) {
  const titleId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [busy, setBusy] = useState(false);
  const [stepUp, setStepUp] = useState(false);
  const [message, setMessage] = useState<PricingNotice | null>(null);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  async function confirm() {
    setBusy(true);
    setMessage(null);
    setStepUp(false);
    const result = await providerCall<SavedVersion>(
      'POST',
      `/${provider.id}/credentials/${version.versionId}/activate`,
      {}
    );
    setBusy(false);
    if (!result.ok) {
      setMessage({ kind: 'error', text: problemText(result.problem) });
      setStepUp(result.problem.code === 'PROVIDER_STEP_UP_REQUIRED');
      return;
    }
    onRolledBack(result.data);
  }

  return (
    <dialog
      aria-labelledby={titleId}
      aria-modal="true"
      className="workbench-section"
      onKeyDown={(event) => {
        if (event.key === 'Escape' && !busy) onClose();
      }}
      open
    >
      <h3 id={titleId}>
        Roll back {provider.displayName} to version {version.versionNo}?
      </h3>
      <p>
        Version {version.versionNo} becomes the active value straight away and WAOOAW will use it without a deployment.
        The value is not read or sent again; the stored version is re-activated.
      </p>
      {signedIn && message === null ? (
        <output className="workbench-hint">{stepUpSignedInText('Confirm roll back')}</output>
      ) : null}
      <PricingMessage message={message} />
      {stepUp ? (
        <StepUpCommand
          payload={{ providerId: provider.id, versionId: version.versionId }}
          pendingKey={`providers.rollback.${provider.id}`}
        />
      ) : null}
      <div className="workbench-actions">
        <button className="primary-command" disabled={busy} onClick={() => void confirm()} type="button">
          {busy ? 'Rolling back...' : 'Confirm roll back'}
        </button>
        <button className="secondary-link" disabled={busy} onClick={onClose} ref={cancelRef} type="button">
          Cancel
        </button>
      </div>
    </dialog>
  );
}

export function ProviderHistory({ provider, history, onReload, onRolledBack }: Props) {
  const [target, setTarget] = useState<CredentialVersion | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const opener = useRef<HTMLButtonElement | null>(null);

  // A roll back changes the live credential, so after the step-up the dialog reopens and waits for the person.
  useResumeAfterStepUp<{ versionId?: unknown }>(
    `providers.rollback.${provider.id}`,
    (payload) => {
      if (history.kind !== 'ready') return;
      const version = history.versions.find(
        (entry) => entry.versionId === payload.versionId && entry.status === 'SUPERSEDED'
      );
      if (!version) return;
      setTarget(version);
      setSignedIn(true);
    },
    history.kind === 'ready'
  );

  function closeDialog() {
    setTarget(null);
    setSignedIn(false);
    opener.current?.focus();
  }

  if (history.kind === 'loading') {
    return <output className="workbench-hint">Loading version history...</output>;
  }
  if (history.kind === 'error') {
    return (
      <div className="workbench-stack">
        <p className="workbench-message workbench-message-error" role="alert">
          {history.text}
        </p>
        <button className="secondary-link" onClick={onReload} type="button">
          Try again
        </button>
      </div>
    );
  }
  if (history.versions.length === 0) {
    return <p className="workbench-hint">No value has been saved for this provider yet.</p>;
  }
  return (
    <div className="workbench-stack">
      <div className="providers-table-wrap">
        <table aria-label={`${provider.displayName} version history`}>
          <thead>
            <tr>
              <th scope="col">Version</th>
              <th scope="col">Status</th>
              <th scope="col">Saved</th>
              <th scope="col">Activated</th>
              <th scope="col">Last test</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {history.versions.map((version) => (
              <tr key={version.versionId}>
                <th scope="row">v{version.versionNo}</th>
                <td>{version.status === 'ACTIVE' ? 'Active' : 'Superseded'}</td>
                <td>{formatWhen(version.createdAt)}</td>
                <td>{formatWhen(version.activatedAt)}</td>
                <td>{version.testOutcome ? outcomeLabel[version.testOutcome] : 'Not tested'}</td>
                <td>
                  {version.status === 'SUPERSEDED' ? (
                    <button
                      className="secondary-link"
                      onClick={(event) => {
                        opener.current = event.currentTarget;
                        setTarget(version);
                      }}
                      type="button"
                    >
                      Roll back to this version
                      <span className="visually-hidden"> (version {version.versionNo})</span>
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {target ? (
        <RollbackDialog
          onClose={closeDialog}
          onRolledBack={(saved) => {
            setTarget(null);
            setSignedIn(false);
            onRolledBack(saved);
          }}
          provider={provider}
          signedIn={signedIn}
          version={target}
        />
      ) : null}
    </div>
  );
}
