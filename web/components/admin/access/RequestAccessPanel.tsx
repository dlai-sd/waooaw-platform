'use client';

// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003
// Constitutional basis: C-009, C-023, C-059, C-063

import { useState } from 'react';
import type { PlatformAccess } from '@/lib/platform-access';

const roleLabels: Record<string, string> = {
  pricing_admin: 'Pricing administrator',
  founder: 'Founder',
};

export function RequestAccessPanel({ access }: { access: PlatformAccess }) {
  const roles = access.requestableRoles;
  const [role, setRole] = useState(roles[0] ?? '');
  const [justification, setJustification] = useState('');
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  if (!access.emailVerified) {
    return (
      <p role="alert">
        Staff access needs a signed-in account whose email address is verified. Verify your email, then come back.
      </p>
    );
  }

  const tooShort = justification.trim().length < 10;
  const pending = access.requests.some((request) => request.status === 'PENDING');

  async function submit() {
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch('/api/platform/access/access-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, justification: justification.trim() }),
      });
      if (response.ok) {
        setMessage({ kind: 'ok', text: 'Request sent. The Founder will review it.' });
        setJustification('');
      } else {
        const problem = (await response.json().catch(() => ({}))) as { detail?: string; title?: string };
        setMessage({ kind: 'error', text: problem.detail ?? problem.title ?? 'The request could not be sent.' });
      }
    } catch {
      setMessage({ kind: 'error', text: 'The request could not be sent. Try again.' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="request-access-title">
      <h2 id="request-access-title">Request staff access</h2>
      <p>
        Signed in as <strong>{access.email}</strong>. Access is granted only after the Founder approves your request.
      </p>
      {access.administrator ? <p>You already hold a staff role.</p> : null}
      <label>
        Role
        <select onChange={(event) => setRole(event.target.value)} value={role}>
          {roles.map((value) => (
            <option key={value} value={value}>
              {roleLabels[value] ?? value}
            </option>
          ))}
        </select>
      </label>
      <label>
        Why do you need it?
        <textarea
          maxLength={500}
          onChange={(event) => setJustification(event.target.value)}
          rows={4}
          value={justification}
        />
      </label>
      <p>
        <button
          className="primary-command"
          disabled={busy || tooShort || role === '' || pending}
          onClick={() => void submit()}
          type="button"
        >
          Send request
        </button>
      </p>
      {pending ? <p>You already have a request waiting for a decision.</p> : null}
      {message ? (
        <p aria-live="polite" role={message.kind === 'error' ? 'alert' : 'status'}>
          {message.text}
        </p>
      ) : null}
      {access.requests.length > 0 ? (
        <ul aria-label="Your requests">
          {access.requests.map((request) => (
            <li key={request.requestId}>
              {roleLabels[request.role] ?? request.role}: {request.status.toLowerCase()}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
