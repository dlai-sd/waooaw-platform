'use client';

// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R009, WC149-R010
// Constitutional basis: C-026, C-059, C-063

import { Facebook } from 'lucide-react';
import { useId, useRef, useState } from 'react';
import {
  formatWhen,
  statusExplanation,
  statusLabel,
  type ConnectionStatus,
  type ProviderConnection,
} from '@/lib/provider-connections-client';
import { PublishForm } from './PublishForm';
import { RevokeDialog } from './RevokeDialog';

type Props = {
  connection: ProviderConnection;
  starting: boolean;
  onReconnect: () => void;
  onRevoked: () => void;
  onChanged: () => void;
};

const tones: Record<ConnectionStatus, string> = { CONNECTED: 'ok', NEEDS_REPAIR: 'bad', REVOKED: 'muted' };

export function ConnectionCard({ connection, starting, onReconnect, onRevoked, onChanged }: Props) {
  const titleId = useId();
  const opener = useRef<HTMLButtonElement>(null);
  const [revoking, setRevoking] = useState(false);
  const [repairPrompted, setRepairPrompted] = useState(false);
  const needsRepair = connection.status === 'NEEDS_REPAIR' || (repairPrompted && connection.status !== 'REVOKED');

  function closeDialog() {
    setRevoking(false);
    opener.current?.focus();
  }

  return (
    <li>
      <section aria-labelledby={titleId} className="workbench-section connections-card">
        <header className="connections-card-heading">
          <div>
            <h2 id={titleId}>
              <Facebook aria-hidden="true" size={20} /> {connection.accountName ?? 'Facebook Page'}
            </h2>
            <p className="workbench-hint">Facebook</p>
          </div>
          <span className="status-label providers-chip" data-tone={tones[connection.status]}>
            {statusLabel[connection.status]}
          </span>
        </header>
        <p>{statusExplanation[connection.status]}</p>
        <dl className="connections-facts">
          <div>
            <dt>Connected on</dt>
            <dd>{formatWhen(connection.connectedAt)}</dd>
          </div>
          <div>
            <dt>Access expires</dt>
            <dd>{formatWhen(connection.expiresAt)}</dd>
          </div>
          {connection.scopes.length > 0 ? (
            <div>
              <dt>Permissions</dt>
              <dd>{connection.scopes.join(', ')}</dd>
            </div>
          ) : null}
        </dl>
        {needsRepair ? (
          <div className="workbench-message workbench-message-error" role="alert">
            <p>
              <strong>Reconnect needed.</strong> WAOOAW cannot publish until you reconnect your Facebook Page.
            </p>
          </div>
        ) : null}
        <div className="workbench-actions">
          {needsRepair ? (
            <button className="primary-command" disabled={starting} onClick={onReconnect} type="button">
              {starting ? 'Opening Facebook...' : 'Reconnect Facebook'}
            </button>
          ) : null}
          {connection.status !== 'REVOKED' ? (
            <button className="secondary-link" onClick={() => setRevoking(true)} ref={opener} type="button">
              Revoke
              <span className="visually-hidden"> the Facebook connection</span>
            </button>
          ) : null}
        </div>
        {connection.status === 'CONNECTED' && !needsRepair ? (
          <PublishForm
            connection={connection}
            onNeedsRepair={() => {
              setRepairPrompted(true);
              onChanged();
            }}
          />
        ) : null}
        {revoking ? <RevokeDialog connection={connection} onClose={closeDialog} onRevoked={onRevoked} /> : null}
      </section>
    </li>
  );
}
