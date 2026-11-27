'use client';

// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R024
// Constitutional basis: C-023, C-042, C-059, C-063

import { useState, type FormEvent } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import {
  actionWords,
  asApproval,
  failureMessage,
  stateExplanation,
  stateWords,
  type ApprovalAction,
  type ProfessionalApproval,
} from '@/lib/professional-approvals';
import { stepUpResumingText, useResumeAfterStepUp } from '@/lib/step-up-resume';

const base = '/api/admin/professionals';
const pendingKey = 'professionals.decision';

type Decision = { professionalType: string; professionalVersion: string; action: ApprovalAction; reason: string };

function asDecision(value: unknown): Decision | null {
  const candidate = value as Partial<Decision> | null;
  if (
    !candidate ||
    typeof candidate.professionalType !== 'string' ||
    typeof candidate.professionalVersion !== 'string' ||
    typeof candidate.reason !== 'string' ||
    !['approve', 'suspend', 'retire'].includes(String(candidate.action))
  )
    return null;
  return candidate as Decision;
}

const when = (value: string | null) =>
  value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '';

export function ProfessionalApprovals({ initial }: { initial: ProfessionalApproval[] }) {
  const [items, setItems] = useState(initial);
  const [choosing, setChoosing] = useState<{ key: string; action: ApprovalAction } | null>(null);
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState('');
  const [stepUp, setStepUp] = useState<Decision | null>(null);

  async function send(decision: Decision) {
    setStepUp(null);
    setMessage('');
    let response: Response;
    try {
      response = await fetch(
        `${base}/${encodeURIComponent(decision.professionalType)}/versions/${encodeURIComponent(decision.professionalVersion)}/${decision.action}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ reason: decision.reason || null }),
        }
      );
    } catch {
      setMessage(failureMessage(null));
      return;
    }
    const body: unknown = await response.json().catch(() => ({}));
    if (response.ok) {
      const saved = asApproval(body);
      if (saved)
        setItems((current) =>
          current.map((item) =>
            item.professionalType === saved.professionalType && item.professionalVersion === saved.professionalVersion
              ? saved
              : item
          )
        );
      setChoosing(null);
      setReason('');
      setMessage(`${actionWords[decision.action]}: saved.`);
      return;
    }
    const code = (body as { code?: unknown } | null)?.code;
    if (response.status === 403 && code === 'PROFESSIONAL_APPROVAL_STEP_UP_REQUIRED') {
      setMessage('Saving a decision needs a fresh strong sign-in. Confirm below and your decision continues.');
      setStepUp(decision);
    } else setMessage(failureMessage(code));
  }

  const resuming = useResumeAfterStepUp<unknown>(pendingKey, async (payload) => {
    const decision = asDecision(payload);
    if (decision) await send(decision);
  });

  function submit(event: FormEvent, item: ProfessionalApproval, action: ApprovalAction) {
    event.preventDefault();
    void send({
      professionalType: item.professionalType,
      professionalVersion: item.professionalVersion,
      action,
      reason: reason.trim(),
    });
  }

  return (
    <div className="portal-stack">
      <output aria-live="polite">{resuming ? stepUpResumingText : message}</output>
      {stepUp ? <StepUpCommand payload={stepUp} pendingKey={pendingKey} /> : null}
      {items.length === 0 ? <p>No professionals are in this release.</p> : null}
      <ul className="portal-stack">
        {items.map((item) => {
          const key = `${item.professionalType}:${item.professionalVersion}`;
          const open = choosing?.key === key ? choosing.action : null;
          return (
            <li className="marketplace-offer" key={key}>
              <header>
                <h2>{item.displayName}</h2>
                <p>
                  Version {item.professionalVersion} · <strong>{stateWords[item.state]}</strong>
                </p>
              </header>
              <p>{stateExplanation[item.state]}</p>
              {item.definitionChanged ? (
                <p role="alert">
                  This professional&apos;s definition changed since you approved it, so customers are stopped until you
                  approve it again.
                </p>
              ) : null}
              {item.decidedBy && item.decidedAt ? (
                <p>
                  Last decision on {when(item.decidedAt)}
                  {item.reason ? `: ${item.reason}` : '.'}
                </p>
              ) : null}
              <div className="command-row">
                {item.actions.map((action) =>
                  action === 'approve' ? (
                    <button
                      className="primary-command"
                      key={action}
                      onClick={() =>
                        void send({
                          professionalType: item.professionalType,
                          professionalVersion: item.professionalVersion,
                          action,
                          reason: '',
                        })
                      }
                      type="button"
                    >
                      {actionWords[action]}
                    </button>
                  ) : (
                    <button
                      className="secondary-link"
                      key={action}
                      onClick={() => {
                        setChoosing({ key, action });
                        setReason('');
                        setMessage('');
                      }}
                      type="button"
                    >
                      {actionWords[action]}
                    </button>
                  )
                )}
              </div>
              {open ? (
                <form className="identity-form" onSubmit={(event) => submit(event, item, open)}>
                  <label>
                    Reason for {open === 'suspend' ? 'suspending' : 'retiring'} (shown to you only)
                    <input
                      maxLength={500}
                      minLength={5}
                      name="reason"
                      onChange={(event) => setReason(event.target.value)}
                      required
                      value={reason}
                    />
                  </label>
                  <div className="command-row">
                    <button className="primary-command" type="submit">
                      Confirm {open === 'suspend' ? 'suspend' : 'retire'}
                    </button>
                    <button className="text-command" onClick={() => setChoosing(null)} type="button">
                      Cancel
                    </button>
                  </div>
                </form>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
