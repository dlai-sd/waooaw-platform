'use client';

// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-AUTH-05
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { CheckCircle2, LoaderCircle, Smartphone } from 'lucide-react';
import { useRef, useState } from 'react';
import type { IdentityVerificationChallenge } from '@/lib/api/generated';
import type { IdentityMessages } from '@/lib/identity-messages';

export function MobileVerificationFlow({ messages, returnTo }: { messages: IdentityMessages; returnTo: string }) {
  const [challenge, setChallenge] = useState<IdentityVerificationChallenge>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const keys = useRef(new Map<string, string>());

  async function command(action: string, fields: Record<string, string>) {
    setPending(true);
    setError('');
    const idempotencyKey = keys.current.get(action) ?? crypto.randomUUID();
    keys.current.set(action, idempotencyKey);
    try {
      const response = await fetch('/api/identity/account', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, idempotencyKey, ...fields }) });
      const body = await response.json();
      if (!response.ok) throw new Error(typeof body.title === 'string' ? body.title : messages.unavailable);
      keys.current.delete(action);
      if ('challengeId' in body) setChallenge(body as IdentityVerificationChallenge);
      else window.location.assign(returnTo);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : messages.unavailable);
    } finally {
      setPending(false);
    }
  }

  return <div className="registration-flow">
    {error ? <p className="identity-error" role="alert">{error}</p> : null}
    {!challenge ? <form className="identity-form" onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); void command('mobile-start', { mobile: String(form.get('mobile') ?? '') }); }}>
      <label>{messages.mobile}<input autoComplete="tel" name="mobile" pattern="^\+[1-9][0-9]{7,14}$" required type="tel" /></label>
      <button className="primary-command" disabled={pending} type="submit">{messages.sendCode} <Smartphone aria-hidden="true" size={18} /></button>
    </form> : <form className="identity-form" onSubmit={(event) => { event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); void command('mobile-confirm', { challengeId: challenge.challengeId, code: String(form.get('code') ?? '') }).finally(() => formElement.reset()); }}>
      <p>{messages.verificationSent} <strong>{challenge.maskedDestination}</strong>.</p>
      <label>{messages.code}<input autoComplete="one-time-code" inputMode="numeric" maxLength={6} minLength={6} name="code" pattern="[0-9]{6}" required /></label>
      <button className="primary-command" disabled={pending} type="submit">{messages.verifyCode} <CheckCircle2 aria-hidden="true" size={18} /></button>
    </form>}
    {pending ? <span aria-live="polite" className="identity-pending"><LoaderCircle aria-hidden="true" className="spin" size={18} /> {messages.working}</span> : null}
  </div>;
}