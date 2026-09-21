'use client';

// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S11
// Constitutional basis: C-001, C-059, C-063

import { MonitorSmartphone, ShieldX } from 'lucide-react';
import { useState } from 'react';
import type { IdentityManagedSession } from '@/lib/api/generated/models/IdentityManagedSession';

export function SessionManager({ initialSessions }: { initialSessions: IdentityManagedSession[] }) {
  const [sessions, setSessions] = useState(initialSessions);
  const [status, setStatus] = useState<string>('');

  async function revoke(sessionId?: string) {
    setStatus('Ending session...');
    const response = await fetch(sessionId ? `/api/identity/sessions/${sessionId}` : '/api/identity/sessions', {
      method: 'DELETE',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
    });
    if (!response.ok) {
      setStatus('The session could not be ended. Try again.');
      return;
    }
    setSessions((current) => (sessionId ? current.filter((session) => session.sessionId !== sessionId) : []));
    setStatus(sessionId ? 'Session ended.' : 'All sessions ended.');
  }

  return (
    <section className="settings-wide" aria-labelledby="active-sessions-title">
      <MonitorSmartphone aria-hidden="true" />
      <h2 id="active-sessions-title">Active sessions</h2>
      {sessions.length ? (
        <ul className="compact-list">
          {sessions.map((session) => (
            <li key={session.sessionId}>
              <strong>{session.current ? 'Current browser' : session.deviceLabel}</strong>{' '}
              <span>
                {session.provider.toLowerCase()} · active {session.lastSeenAt.toLocaleString()}
              </span>{' '}
              <button type="button" onClick={() => void revoke(session.sessionId)}>
                <ShieldX aria-hidden="true" size={16} /> End session
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p>No active sessions.</p>
      )}
      {sessions.length > 1 ? (
        <button className="secondary-command" type="button" onClick={() => void revoke()}>
          <ShieldX aria-hidden="true" size={16} /> End all sessions
        </button>
      ) : null}
      <output aria-live="polite">{status}</output>
    </section>
  );
}
