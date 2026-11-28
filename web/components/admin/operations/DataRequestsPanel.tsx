'use client';

// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-049, C-059, C-063, C-078

import { useCallback, useEffect, useState } from 'react';

type OpenRequest = { requestId: string; tenantId: string; kind: 'EXPORT' | 'ERASURE'; requestedAt: string };

const kindText = { EXPORT: 'Copy of data', ERASURE: 'Erase account' } as const;

// The Founder's task list for customers' data copy and erasure requests. Closing one needs a note and a fresh sign-in.
export function DataRequestsPanel({ canResolve }: { canResolve: boolean }) {
  const [items, setItems] = useState<OpenRequest[] | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    setFailed(false);
    try {
      const response = await fetch('/api/operations/data-requests', { cache: 'no-store' });
      if (!response.ok) throw new Error('unavailable');
      setItems(((await response.json()) as { items: OpenRequest[] }).items);
    } catch {
      setItems([]);
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function resolve(request: OpenRequest, completed: boolean) {
    const note = (notes[request.requestId] ?? '').trim();
    if (!note) {
      setMessage('Write what was done, or why it was declined, before closing the request.');
      return;
    }
    const response = await fetch(`/api/operations/data-requests/${request.requestId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schemaVersion: '1.0.0', completed, note }),
    });
    if (response.status === 403) setMessage('Closing a request needs a fresh strong sign-in. Sign in again and retry.');
    else if (!response.ok) setMessage('The request could not be closed. Nothing was changed.');
    else {
      setMessage('The request was closed and the customer can see it.');
      await load();
    }
  }

  return (
    <section aria-labelledby="ops-data-requests">
      <h2 id="ops-data-requests">Customer data requests</h2>
      {failed ? (
        <p role="alert">
          The list could not be loaded.{' '}
          <button onClick={() => void load()} type="button">
            Try again
          </button>
        </p>
      ) : items === null ? (
        <output>Loading requests…</output>
      ) : items.length === 0 ? (
        <p>No customer is waiting for a copy of their data or an erasure.</p>
      ) : (
        <ul className="compact-list">
          {items.map((request) => (
            <li key={request.requestId}>
              <strong>{kindText[request.kind]}</strong> for customer {request.tenantId}, asked on{' '}
              {new Date(request.requestedAt).toLocaleDateString()}
              {canResolve ? (
                <>
                  <label>
                    Note
                    <input
                      onChange={(event) =>
                        setNotes((current) => ({ ...current, [request.requestId]: event.target.value }))
                      }
                      value={notes[request.requestId] ?? ''}
                    />
                  </label>
                  <button onClick={() => void resolve(request, true)} type="button">
                    Mark done
                  </button>
                  <button onClick={() => void resolve(request, false)} type="button">
                    Decline
                  </button>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <output aria-live="polite">{message}</output>
    </section>
  );
}
