'use client';

// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-049 (Honest Limitation), C-059, C-063, C-078

import { useCallback, useEffect, useState } from 'react';

type DataRequest = {
  requestId: string;
  kind: 'EXPORT' | 'ERASURE';
  state: 'RECEIVED' | 'COMPLETED' | 'DECLINED';
  requestedAt: string;
  resolvedAt?: string | null;
  resolutionNote?: string | null;
};

const kindLabel = { EXPORT: 'Copy of your data', ERASURE: 'Erase your account' } as const;
const stateLabel = {
  RECEIVED: 'Received. The WAOOAW team will handle it.',
  COMPLETED: 'Done',
  DECLINED: 'Could not be done',
} as const;

export function DataRightsPanel() {
  const [requests, setRequests] = useState<DataRequest[] | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirmErase, setConfirmErase] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await fetch('/api/customer-data-requests', { cache: 'no-store' });
      if (!response.ok) throw new Error('unavailable');
      const body = (await response.json()) as { items: DataRequest[] };
      setRequests(body.items);
    } catch {
      setRequests([]);
      setMessage('Your earlier requests could not be loaded. You can still send a new one.');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function send(kind: DataRequest['kind']) {
    setBusy(true);
    setMessage('');
    try {
      const response = await fetch('/api/customer-data-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify({ schemaVersion: '1.0.0', kind }),
      });
      if (response.status === 403) {
        setMessage('Only the account owner can ask for this.');
      } else if (!response.ok) {
        setMessage('Your request could not be sent. Nothing was changed. Please try again.');
      } else {
        setMessage(
          response.status === 200
            ? 'You already have this request open. We will not send it twice.'
            : 'Your request was received. The WAOOAW team will handle it and you will see its status here.'
        );
        setConfirmErase(false);
        await load();
      }
    } catch {
      setMessage('Your request could not be sent. Nothing was changed. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  const open = (kind: DataRequest['kind']) =>
    requests?.some((request) => request.kind === kind && request.state === 'RECEIVED') ?? false;

  return (
    <section className="settings-wide" aria-labelledby="data-rights-heading">
      <h2 id="data-rights-heading">Your data</h2>
      <p>
        You can ask for a copy of your data, or ask for your account to be erased. Asking does not erase anything by
        itself: the WAOOAW team receives your request, checks it with you, and you see its status below. Records we must
        keep by law, such as tax invoices, are kept and not erased.
      </p>
      <div className="portal-form portal-form-inline">
        <button
          className="secondary-link"
          disabled={busy || open('EXPORT')}
          onClick={() => void send('EXPORT')}
          type="button"
        >
          Ask for a copy of my data
        </button>
        {confirmErase ? (
          <>
            <p role="alert">
              Erasing your account stops your agents and removes your data. This cannot be undone. Are you sure you want
              to send this request?
            </p>
            <button className="primary-command" disabled={busy} onClick={() => void send('ERASURE')} type="button">
              Yes, ask for my account to be erased
            </button>
            <button className="secondary-link" disabled={busy} onClick={() => setConfirmErase(false)} type="button">
              No, keep my account
            </button>
          </>
        ) : (
          <button
            className="secondary-link"
            disabled={busy || open('ERASURE')}
            onClick={() => setConfirmErase(true)}
            type="button"
          >
            Ask for my account to be erased
          </button>
        )}
      </div>
      <output aria-live="polite">{message}</output>
      {requests && requests.length > 0 ? (
        <ul className="compact-list">
          {requests.map((request) => (
            <li key={request.requestId}>
              {kindLabel[request.kind]}: {stateLabel[request.state]}
              {request.resolutionNote ? ` ${request.resolutionNote}` : ''}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
