'use client';

// Implements: architecture/reference/ux/wc-034-implementation-decomposition.md §F2
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { ArrowRight, CheckCircle2, LoaderCircle, Mail, Smartphone } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { RegistrationProgress } from '@/components/auth/RegistrationProgress';
import { identitySessionChangeKey } from '@/components/auth/SignOutCommand';
import type { IdentityRegistration, IdentityVerificationChallenge } from '@/lib/api/generated';
import type { IdentityMessages } from '@/lib/identity-messages';
import type { SupportedLocale } from '@/lib/preferences';

type Draft = { displayName: string; businessName: string; businessDomain: string };
type Command = Record<string, string> & { action: string };
const draftKey = 'waooaw:identity:registration-draft';

export function RegistrationFlow({ locale, messages, returnTo = '/home' }: { locale: SupportedLocale; messages: IdentityMessages; returnTo?: string }) {
  const router = useRouter();
  const [registration, setRegistration] = useState<IdentityRegistration>();
  const [challenge, setChallenge] = useState<IdentityVerificationChallenge>();
  const [draft, setDraft] = useState<Draft>({ displayName: '', businessName: '', businessDomain: '' });
  const [pending, setPending] = useState(true);
  const [error, setError] = useState('');
  const [voluntaryMobile, setVoluntaryMobile] = useState(false);
  const keys = useRef(new Map<string, string>());
  const activeRequest = useRef<AbortController>();

  async function command(commandBody: Command) {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    const timeout = setTimeout(() => controller.abort(), 20_000);
    setPending(true);
    setError('');
    const key = keys.current.get(commandBody.action) ?? crypto.randomUUID();
    keys.current.set(commandBody.action, key);
    try {
      const response = await fetch('/api/identity/registration', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...commandBody, idempotencyKey: key }), signal: controller.signal });
      const body = await response.json();
      if (activeRequest.current !== controller) return;
      if (controller.signal.aborted) throw new Error();
      if (!response.ok) {
        if (response.status === 401) {
          setChallenge(undefined);
          setRegistration(undefined);
        }
        throw new Error();
      }
      if ((commandBody.action === 'start' || commandBody.action === 'complete') && body?.handoffConfirmed === true) {
        keys.current.delete(commandBody.action);
        sessionStorage.removeItem(draftKey);
        router.replace(returnTo);
        router.refresh();
        return;
      }
      if (commandBody.action === 'complete') throw new Error();
      keys.current.delete(commandBody.action);
      if ('challengeId' in body) setChallenge(body as IdentityVerificationChallenge);
      else {
        setChallenge(undefined);
        setRegistration(body as IdentityRegistration);
      }
      return body;
    } catch {
      if (activeRequest.current === controller) setError(messages.unavailable);
    } finally {
      clearTimeout(timeout);
      if (activeRequest.current === controller) {
        activeRequest.current = undefined;
        setPending(false);
      }
    }
  }

  useEffect(() => {
    function handleSessionChange(event: StorageEvent) {
      if (event.key !== identitySessionChangeKey || event.storageArea !== localStorage) return;
      activeRequest.current?.abort();
      activeRequest.current = undefined;
      sessionStorage.removeItem(draftKey);
      setChallenge(undefined);
      setRegistration(undefined);
      router.replace('/');
      router.refresh();
    }
    const saved = sessionStorage.getItem(draftKey);
    if (saved) {
      try { setDraft(JSON.parse(saved) as Draft); } catch { sessionStorage.removeItem(draftKey); }
    }
    window.addEventListener('storage', handleSessionChange);
    void command({ action: 'start', languagePreference: locale });
    return () => {
      window.removeEventListener('storage', handleSessionChange);
      activeRequest.current?.abort();
      activeRequest.current = undefined;
    };
    // Registration bootstrap is keyed only to locale; retries reuse the retained command key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locale]);

  function updateDraft(field: keyof Draft, value: string) {
    const next = { ...draft, [field]: value };
    setDraft(next);
    sessionStorage.setItem(draftKey, JSON.stringify(next));
  }

  function registrationCommand(action: string, fields: Record<string, string> = {}) {
    if (!registration) return Promise.resolve(undefined);
    return command({ action, registrationId: registration.registrationId, ...fields });
  }

  function verificationForm(purpose: 'email' | 'mobile') {
    const isEmail = purpose === 'email';
    if (!challenge) return <form className="identity-form" onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); void registrationCommand(`${purpose}-start`, { [purpose]: String(form.get(purpose) ?? '') }); }}>
      <label>{isEmail ? messages.email : messages.mobile}<input autoComplete={isEmail ? 'email' : 'tel'} name={purpose} required type={isEmail ? 'email' : 'tel'} pattern={isEmail ? undefined : String.raw`^\+[1-9][0-9]{7,14}$`} /></label>
      <button className="primary-command" disabled={pending} type="submit">{messages.sendCode} <Mail aria-hidden="true" size={18} /></button>
    </form>;
    return <form className="identity-form" onSubmit={(event) => { event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); const code = String(form.get('code') ?? ''); void registrationCommand(`${purpose}-confirm`, { challengeId: challenge.challengeId, code }).finally(() => formElement.reset()); }}>
      <p>{messages.verificationSent} <strong>{challenge.maskedDestination}</strong>.</p>
      <label>{messages.code}<input autoComplete="one-time-code" inputMode="numeric" maxLength={6} minLength={6} name="code" pattern="[0-9]{6}" required /></label>
      <button className="primary-command" disabled={pending} type="submit">{messages.verifyCode} <CheckCircle2 aria-hidden="true" size={18} /></button>
    </form>;
  }

  if (!registration) return <div aria-live="polite" className="identity-status">{pending ? <><LoaderCircle aria-hidden="true" className="spin" /> {messages.working}</> : <><p>{error || messages.unavailable}</p><button className="primary-command" type="button" onClick={() => void command({ action: 'start', languagePreference: locale })}>{messages.retry}</button></>}</div>;

  const action = voluntaryMobile ? 'VERIFY_MOBILE' : registration.nextAction;
  return <div className="registration-flow">
    <RegistrationProgress action={action} pending={pending} />
    {error ? <p className="identity-error" role="alert">{error}</p> : null}
    {action === 'COMPLETE_PROFILE' ? <form className="identity-form" onSubmit={(event) => { event.preventDefault(); void registrationCommand('profile', { ...draft, languagePreference: locale }); }}>
      <label>{messages.displayName}<input autoComplete="name" maxLength={120} onChange={(event) => updateDraft('displayName', event.target.value)} required value={draft.displayName} /></label>
      <label>{messages.businessName}<input autoComplete="organization" maxLength={160} onChange={(event) => updateDraft('businessName', event.target.value)} required value={draft.businessName} /></label>
      <label>{messages.businessDomain}<input maxLength={100} onChange={(event) => updateDraft('businessDomain', event.target.value)} required value={draft.businessDomain} /></label>
      <button className="primary-command" disabled={pending} type="submit">{messages.saveProfile} <ArrowRight aria-hidden="true" size={18} /></button>
    </form> : null}
    {action === 'VERIFY_EMAIL' ? verificationForm('email') : null}
    {action === 'VERIFY_MOBILE' ? verificationForm('mobile') : null}
    {action === 'COMPLETE_REGISTRATION' ? <div className="identity-choice"><Smartphone aria-hidden="true" size={28} /><p>{messages.optionalMobile}</p><div className="command-row"><button className="primary-command" disabled={pending} type="button" onClick={() => setVoluntaryMobile(true)}>{messages.optionalMobile}</button><button className="text-command" disabled={pending} type="button" onClick={() => void registrationCommand('complete')}>{messages.complete}</button></div></div> : null}
    {action === 'RESOLVE_DUPLICATE' ? <p role="status">{messages.duplicate}</p> : null}
    {(action === 'CONTINUE_TO_DEFAULT_TARGET' || action === 'NONE') ? <button className="primary-command" disabled={pending} type="button" onClick={() => void registrationCommand('complete')}>{messages.complete}</button> : null}
    {pending ? <span aria-live="polite" className="identity-pending"><LoaderCircle aria-hidden="true" className="spin" size={18} /> {messages.working}</span> : null}
  </div>;
}