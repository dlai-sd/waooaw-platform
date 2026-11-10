'use client';

import { useRef, useState } from 'react';
import { SignOutCommand } from '@/components/auth/SignOutCommand';

type State = {
  challengeId: string;
  state: 'OTP_REQUIRED' | 'DELIVERY_UNRESOLVED' | 'EXPIRED' | 'COMPLETED';
  maskedMobile: string;
  expiresAt: string;
  relationshipApprovalRequired: true;
};
type Command = 'START' | 'CONFIRM' | 'CANCEL' | 'STATUS';

function isState(value: unknown): value is State {
  return (
    value !== null &&
    typeof value === 'object' &&
    'challengeId' in value &&
    typeof value.challengeId === 'string' &&
    'state' in value &&
    ['OTP_REQUIRED', 'DELIVERY_UNRESOLVED', 'EXPIRED', 'COMPLETED'].includes(String(value.state)) &&
    'maskedMobile' in value &&
    typeof value.maskedMobile === 'string' &&
    'expiresAt' in value &&
    typeof value.expiresAt === 'string' &&
    Number.isFinite(Date.parse(value.expiresAt)) &&
    'relationshipApprovalRequired' in value &&
    value.relationshipApprovalRequired === true
  );
}

export function WhatsAppPhoneChange({
  onCompleted,
}: {
  onCompleted: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<State>();
  const [mobile, setMobile] = useState('');
  const [code, setCode] = useState('');
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [recoveryRequired, setRecoveryRequired] = useState(false);
  const keys = useRef<Partial<Record<Command, string>>>({});
  const unresolvedConfirmation = useRef(false);

  async function command(action: Command) {
    if (busy) return;
    setBusy(true);
    setError('');
    if (action !== 'STATUS') keys.current[action] ??= crypto.randomUUID();
    if (action === 'CONFIRM') unresolvedConfirmation.current = true;
    try {
      const response = await fetch('/api/identity/phone-changes', {
        method: 'POST',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: action,
          ...(action !== 'STATUS' ? { idempotencyKey: keys.current[action] } : {}),
          ...(action === 'START' ? { mobile } : {}),
          ...(action === 'CONFIRM' || action === 'CANCEL' ? { challengeId: state?.challengeId } : {}),
          ...(action === 'CONFIRM' ? { code, consent } : {}),
        }),
      });
      if (response.status === 204) {
        setState(undefined);
        setRecoveryRequired(false);
        return;
      }
      const value: unknown = await response.json();
      if (!response.ok) {
        if (response.status >= 500) setRecoveryRequired(true);
        const fresh =
          response.status === 401 ||
          (response.status === 403 &&
            value !== null &&
            typeof value === 'object' &&
            'code' in value &&
            value.code === 'IDENTITY_STEP_UP_REQUIRED');
        setError(
          fresh
            ? 'fresh-sign-in'
            : response.status === 429
              ? 'limited'
              : response.status === 410
                ? 'expired'
                : response.status === 403
                  ? 'denied'
                  : 'unavailable'
        );
        return;
      }
      if (!isState(value)) throw new Error('Phone-change response is invalid.');
      setRecoveryRequired(false);
      setState(value);
      setMobile('');
      setCode('');
      if (value.state === 'COMPLETED' && unresolvedConfirmation.current) {
        unresolvedConfirmation.current = false;
        onCompleted();
      }
    } catch {
      setError('unavailable');
      setRecoveryRequired(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="whatsapp-phone-change-heading">
      <h3 id="whatsapp-phone-change-heading">Change your WhatsApp number</h3>
      <p>Sign in freshly to your existing account. A code proves control of the new number, not account ownership.</p>
      {!open ? (
        <button
          type="button"
          onClick={() => {
            setOpen(true);
            void command('STATUS');
          }}
        >
          Change number
        </button>
      ) : (
        <>
          {state?.state === 'OTP_REQUIRED' ? (
            <>
              <p>
                Code sent to {state.maskedMobile}. Expires at {new Date(state.expiresAt).toLocaleString()}.
              </p>
              <label>
                Verification code
                <input
                  aria-label="New number verification code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={code}
                  disabled={busy}
                  onChange={(event) => {
                    setCode(event.target.value);
                    keys.current.CONFIRM = undefined;
                  }}
                />
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={consent}
                  disabled={busy}
                  onChange={(event) => setConsent(event.target.checked)}
                />
                I approve replacing my number and revoking old WhatsApp access. My history stays with this account. I
                must link the new number and approve each professional relationship again.
              </label>
              <button
                type="button"
                disabled={busy || recoveryRequired || !consent || !/^[0-9]{6}$/.test(code)}
                onClick={() => void command('CONFIRM')}
              >
                Verify and change number
              </button>
            </>
          ) : state?.state === 'DELIVERY_UNRESOLVED' ? (
            <p>
              <output>Delivery is unresolved. Check status; we will not resend automatically.</output>
            </p>
          ) : state?.state === 'COMPLETED' ? (
            <p>
              <output>
                Number changed. Link your new number below and approve each professional relationship separately.
              </output>
            </p>
          ) : null}
          {state?.state === 'OTP_REQUIRED' || state?.state === 'DELIVERY_UNRESOLVED' ? (
            <>
              <button type="button" disabled={busy} onClick={() => void command('CANCEL')}>
                Cancel phone change
              </button>
            </>
          ) : (
            <>
              <label>
                New WhatsApp number
                <input
                  aria-label="New WhatsApp number"
                  type="tel"
                  autoComplete="off"
                  value={mobile}
                  maxLength={16}
                  disabled={busy}
                  onChange={(event) => {
                    setMobile(event.target.value);
                    keys.current.START = undefined;
                  }}
                />
              </label>
              <button
                type="button"
                disabled={busy || recoveryRequired || !/^\+[1-9][0-9]{7,14}$/.test(mobile)}
                onClick={() => void command('START')}
              >
                Send verification code
              </button>
            </>
          )}
          <button type="button" disabled={busy} onClick={() => void command('STATUS')}>
            Check phone-change status
          </button>
          {error === 'fresh-sign-in' ? (
            <div role="alert">
              Fresh sign-in is required.
              <SignOutCommand label="Sign out, then sign in again" />
            </div>
          ) : error ? (
            <p role="alert">
              {error === 'limited'
                ? 'Requests are temporarily limited.'
                : error === 'expired'
                  ? 'The code has expired. Cancel and start a new request.'
                  : error === 'denied'
                    ? 'Change denied. Check your code or use separate account recovery for a conflicting number.'
                    : 'Outcome unavailable. Check status before retrying; do not assume your number changed.'}
            </p>
          ) : null}
          <p>
            Cannot sign in, or the number belongs to another account? Use separate account recovery. OTP alone cannot
            transfer an account.
          </p>
        </>
      )}
    </section>
  );
}
