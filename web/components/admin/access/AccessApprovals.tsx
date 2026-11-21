'use client';

// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063, C-065

import { signIn } from 'next-auth/react';
import { useCallback, useEffect, useState } from 'react';
import type { PlatformAccessRequest, PlatformGrant } from '@/lib/platform-access';

type Problem = { code?: string; detail?: string };

const base = '/api/platform/access';

async function call(path: string, method: 'GET' | 'POST', body?: unknown): Promise<{ ok: boolean; data: unknown }> {
  const response = await fetch(`${base}/${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: 'no-store',
  });
  return { ok: response.ok, data: await response.json().catch(() => ({})) };
}

export function AccessApprovals() {
  const [requests, setRequests] = useState<PlatformAccessRequest[]>([]);
  const [grants, setGrants] = useState<PlatformGrant[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [stepUp, setStepUp] = useState(false);

  const load = useCallback(async () => {
    const [pending, active] = await Promise.all([call('access-requests?status=PENDING', 'GET'), call('grants', 'GET')]);
    if (pending.ok) setRequests((pending.data as { requests: PlatformAccessRequest[] }).requests);
    if (active.ok) setGrants((active.data as { grants: PlatformGrant[] }).grants);
    if (!pending.ok || !active.ok) setMessage('Access management could not be loaded.');
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(request: PlatformAccessRequest, decision: 'APPROVE' | 'REJECT') {
    setMessage(null);
    setStepUp(false);
    const result = await call(`access-requests/${request.requestId}/decision`, 'POST', { decision });
    if (result.ok) {
      setMessage(`${request.email}: ${decision === 'APPROVE' ? 'approved' : 'rejected'}.`);
      await load();
      return;
    }
    const problem = result.data as Problem;
    setStepUp(problem.code === 'PLATFORM_ACCESS_STEP_UP_REQUIRED');
    setMessage(problem.detail ?? 'The decision could not be saved.');
  }

  async function revoke(grant: PlatformGrant) {
    const reason = window.prompt(`Why is ${grant.email} losing ${grant.role}?`)?.trim();
    if (!reason) return;
    const result = await call(`grants/${grant.grantId}/revoke`, 'POST', { reason });
    setMessage(result.ok ? `${grant.email}: access removed.` : ((result.data as Problem).detail ?? 'Not removed.'));
    if (result.ok) await load();
  }

  return (
    <section aria-labelledby="access-approvals-title">
      <h1 id="access-approvals-title">Staff access</h1>
      {message ? <output aria-live="polite">{message}</output> : null}
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

      <h2>Waiting for your decision</h2>
      {requests.length === 0 ? <p>No requests are waiting.</p> : null}
      <ul aria-label="Pending requests">
        {requests.map((request) => (
          <li key={request.requestId}>
            <strong>{request.email}</strong> asks for <strong>{request.role}</strong>
            <br />
            <q>{request.justification}</q>
            <br />
            <button className="primary-command" onClick={() => void decide(request, 'APPROVE')} type="button">
              Approve
            </button>{' '}
            <button className="secondary-link" onClick={() => void decide(request, 'REJECT')} type="button">
              Reject
            </button>
          </li>
        ))}
      </ul>

      <h2>Who holds a staff role</h2>
      <ul aria-label="Active grants">
        {grants.map((grant) => (
          <li key={grant.grantId}>
            {grant.email}: {grant.role} ({grant.source === 'CONFIG' ? 'set in the environment' : 'approved'})
            {grant.revocable ? (
              <>
                {' '}
                <button className="secondary-link" onClick={() => void revoke(grant)} type="button">
                  Remove
                </button>
              </>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
