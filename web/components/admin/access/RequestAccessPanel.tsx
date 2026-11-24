'use client';

// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003
// Constitutional basis: C-009, C-023, C-059, C-063

import { useState } from 'react';
import type { PlatformAccess } from '@/lib/platform-access';

const roleLabels: Record<string, string> = {
  pricing_admin: 'Pricing administrator',
  founder: 'Founder',
};

export function RequestAccessPanel({ access, subject = null }: { access: PlatformAccess; subject?: string | null }) {
  const roles = access.requestableRoles;
  const [role, setRole] = useState(roles[0] ?? '');
  const [justification, setJustification] = useState('');
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  if (!access.emailVerified) {
    return (
      <section aria-labelledby="request-access-title" className="workbench-section">
        <h2 id="request-access-title">Request staff access</h2>
        <p className="workbench-message workbench-message-error" role="alert">
          Staff access needs a signed-in account whose email address is verified. Verify your email, then come back.
        </p>
      </section>
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
    <section aria-labelledby="request-access-title" className="workbench-section">
      <h2 id="request-access-title">Request staff access</h2>
      <p>
        Signed in as <strong>{access.email}</strong>. Access is granted only after the Founder approves your request.
      </p>
      {subject ? (
        <p className="workbench-hint">
          Your sign-in ID: <code className="access-subject">{subject}</code>. A role is tied to this ID as well as to
          your email, so if it does not appear after you sign in a different way, give this ID to the Founder.
        </p>
      ) : null}
      {access.administrator ? <p>You already hold a staff role.</p> : null}
      <form
        className="workbench-form access-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label className="access-field">
          <span>Role</span>
          <select onChange={(event) => setRole(event.target.value)} value={role}>
            {roles.map((value) => (
              <option key={value} value={value}>
                {roleLabels[value] ?? value}
              </option>
            ))}
          </select>
        </label>
        <label className="access-field">
          <span>Why do you need it?</span>
          <textarea
            maxLength={500}
            onChange={(event) => setJustification(event.target.value)}
            rows={4}
            value={justification}
          />
        </label>
        <p className="workbench-hint">At least 10 characters, up to 500.</p>
        <div className="workbench-actions">
          <button className="primary-command" disabled={busy || tooShort || role === '' || pending} type="submit">
            Send request
          </button>
        </div>
      </form>
      {pending ? <p className="workbench-hint">You already have a request waiting for a decision.</p> : null}
      {message ? (
        <p
          aria-live="polite"
          className={`workbench-message ${message.kind === 'error' ? 'workbench-message-error' : 'workbench-message-success'}`}
          role={message.kind === 'error' ? 'alert' : 'status'}
        >
          {message.text}
        </p>
      ) : null}
      {access.requests.length > 0 ? (
        <ul aria-label="Your requests" className="access-list">
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
