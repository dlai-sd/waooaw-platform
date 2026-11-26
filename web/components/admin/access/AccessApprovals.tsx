'use client';

// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-059, C-063, C-065

import { useCallback, useEffect, useState } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import type { PlatformAccessRequest, PlatformGrant } from '@/lib/platform-access';
import { stepUpResumingText, useResumeAfterStepUp } from '@/lib/step-up-resume';

type Problem = { code?: string; detail?: string };
type Decision = 'APPROVE' | 'REJECT';
type PendingDecision = { requestId: string; email: string; decision: Decision };
type Remote<T> = { status: 'loading' } | { status: 'loaded'; data: T } | { status: 'failed'; message: string };

const base = '/api/platform/access';
const decisionKey = 'access.decision';

async function call(path: string, method: 'GET' | 'POST', body?: unknown): Promise<{ ok: boolean; data: unknown }> {
  try {
    const response = await fetch(`${base}/${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store',
    });
    return { ok: response.ok, data: await response.json().catch(() => ({})) };
  } catch {
    return { ok: false, data: {} };
  }
}

function asPendingDecision(value: unknown): PendingDecision | null {
  const candidate = value as Partial<PendingDecision> | null;
  if (
    !candidate ||
    typeof candidate.requestId !== 'string' ||
    typeof candidate.email !== 'string' ||
    (candidate.decision !== 'APPROVE' && candidate.decision !== 'REJECT')
  )
    return null;
  return { requestId: candidate.requestId, email: candidate.email, decision: candidate.decision };
}

function LoadProblem({ state, onRetry }: { state: Remote<unknown>; onRetry: () => void }) {
  if (state.status === 'loading') return <output aria-busy="true">Loading…</output>;
  if (state.status === 'failed') {
    return (
      <div className="workbench-actions">
        <p className="workbench-message" role="alert">
          {state.message}
        </p>
        <button className="secondary-link" onClick={onRetry} type="button">
          Retry
        </button>
      </div>
    );
  }
  return null;
}

export function AccessApprovals() {
  const [requests, setRequests] = useState<Remote<PlatformAccessRequest[]>>({ status: 'loading' });
  const [grants, setGrants] = useState<Remote<PlatformGrant[]>>({ status: 'loading' });
  const [message, setMessage] = useState<string | null>(null);
  const [stepUp, setStepUp] = useState<PendingDecision | null>(null);

  const loadRequests = useCallback(async () => {
    const result = await call('access-requests?status=PENDING', 'GET');
    const list = (result.data as { requests?: PlatformAccessRequest[] } | null)?.requests;
    setRequests(
      result.ok && Array.isArray(list)
        ? { status: 'loaded', data: list }
        : { status: 'failed', message: 'The requests waiting for a decision could not be loaded.' }
    );
  }, []);

  const loadGrants = useCallback(async () => {
    const result = await call('grants', 'GET');
    const list = (result.data as { grants?: PlatformGrant[] } | null)?.grants;
    setGrants(
      result.ok && Array.isArray(list)
        ? { status: 'loaded', data: list }
        : { status: 'failed', message: 'The people who hold a staff role could not be loaded.' }
    );
  }, []);

  const load = useCallback(() => Promise.all([loadRequests(), loadGrants()]), [loadRequests, loadGrants]);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(pending: PendingDecision) {
    setMessage(null);
    setStepUp(null);
    const result = await call(`access-requests/${pending.requestId}/decision`, 'POST', {
      decision: pending.decision,
    });
    if (result.ok) {
      setMessage(`${pending.email}: ${pending.decision === 'APPROVE' ? 'approved' : 'rejected'}.`);
      await load();
      return;
    }
    const problem = result.data as Problem;
    if (problem.code === 'PLATFORM_ACCESS_STEP_UP_REQUIRED') setStepUp(pending);
    setMessage(problem.detail ?? 'The decision could not be saved.');
  }

  const choose = (request: PlatformAccessRequest, decision: Decision) =>
    decide({ requestId: request.requestId, email: request.email, decision });

  const resuming = useResumeAfterStepUp<unknown>(decisionKey, async (payload) => {
    const pending = asPendingDecision(payload);
    if (pending) await decide(pending);
  });

  async function revoke(grant: PlatformGrant) {
    const reason = window.prompt(`Why is ${grant.email} losing ${grant.role}?`)?.trim();
    if (!reason) return;
    const result = await call(`grants/${grant.grantId}/revoke`, 'POST', { reason });
    setMessage(result.ok ? `${grant.email}: access removed.` : ((result.data as Problem).detail ?? 'Not removed.'));
    if (result.ok) await load();
  }

  return (
    <section aria-labelledby="access-approvals-title" className="workbench-stack">
      <h2 id="access-approvals-title">Decide on staff access</h2>
      {resuming || message ? (
        <output aria-live="polite" className="workbench-message">
          {resuming ? stepUpResumingText : message}
        </output>
      ) : null}
      {stepUp ? <StepUpCommand payload={stepUp} pendingKey={decisionKey} /> : null}

      <section aria-labelledby="access-waiting-title" className="workbench-section">
        <h3 id="access-waiting-title">Waiting for your decision</h3>
        <LoadProblem
          onRetry={() => {
            setRequests({ status: 'loading' });
            void loadRequests();
          }}
          state={requests}
        />
        {requests.status === 'loaded' && requests.data.length === 0 ? (
          <p className="workbench-hint">No requests are waiting.</p>
        ) : null}
        <ul aria-label="Pending requests" className="connections-list">
          {(requests.status === 'loaded' ? requests.data : []).map((request) => (
            <li className="workbench-section access-card" key={request.requestId}>
              <p>
                <strong>{request.email}</strong> asks for <strong>{request.role}</strong>
              </p>
              <p>
                <q>{request.justification}</q>
              </p>
              <div className="workbench-actions">
                <button className="primary-command" onClick={() => void choose(request, 'APPROVE')} type="button">
                  Approve
                </button>
                <button className="secondary-link" onClick={() => void choose(request, 'REJECT')} type="button">
                  Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="access-holders-title" className="workbench-section">
        <h3 id="access-holders-title">Who holds a staff role</h3>
        <LoadProblem
          onRetry={() => {
            setGrants({ status: 'loading' });
            void loadGrants();
          }}
          state={grants}
        />
        <ul aria-label="Active grants" className="connections-list">
          {(grants.status === 'loaded' ? grants.data : []).map((grant) => (
            <li className="workbench-section access-card" key={grant.grantId}>
              <p>
                {grant.email}: {grant.role} ({grant.source === 'CONFIG' ? 'set in the environment' : 'approved'})
              </p>
              {grant.revocable ? (
                <div className="workbench-actions">
                  <button className="secondary-link" onClick={() => void revoke(grant)} type="button">
                    Remove
                  </button>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
    </section>
  );
}
