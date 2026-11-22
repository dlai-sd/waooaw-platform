'use client';

// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R010
// Constitutional basis: C-026, C-059, C-063

import { useEffect, useId, useRef, useState } from 'react';
import { PricingMessage, type PricingNotice } from '@/components/admin/pricing/usePricingCommand';
import { connectionCall } from '@/lib/provider-connections-call';
import { problemText, type ProviderConnection } from '@/lib/provider-connections-client';

type Props = {
  connection: ProviderConnection;
  onClose: () => void;
  onRevoked: () => void;
};

export function RevokeDialog({ connection, onClose, onRevoked }: Props) {
  const titleId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<PricingNotice | null>(null);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  async function confirm() {
    setBusy(true);
    setMessage(null);
    const result = await connectionCall<unknown>('POST', `/${connection.id}/revoke`, {});
    if (result.ok) {
      onRevoked();
      return;
    }
    setMessage({ kind: 'error', text: problemText(result.problem) });
    setBusy(false);
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
        Revoke the Facebook connection{connection.accountName ? ` for ${connection.accountName}` : ''}?
      </h3>
      <p>
        WAOOAW deletes its stored access straight away and can no longer publish to your Facebook Page. You can connect
        again later. Posts already published stay on Facebook.
      </p>
      <PricingMessage message={message} />
      <div className="workbench-actions">
        <button className="primary-command" disabled={busy} onClick={() => void confirm()} type="button">
          {busy ? 'Revoking...' : 'Confirm revoke'}
        </button>
        <button className="secondary-link" disabled={busy} onClick={onClose} ref={cancelRef} type="button">
          Cancel
        </button>
      </div>
    </dialog>
  );
}
