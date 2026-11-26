'use client';

// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { Plus } from 'lucide-react';
import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import { PricingMessage, type PricingNotice } from '@/components/admin/pricing/usePricingCommand';
import { providerCall } from '@/lib/provider-admin-call';
import {
  problemText,
  providerNamePattern,
  type CreateProviderInput,
  type ProviderCategory,
  type ProviderSummary,
  type TestAuthScheme,
} from '@/lib/provider-admin-client';
import { stepUpSignedInText, useResumeAfterStepUp } from '@/lib/step-up-resume';

type Props = { onCreated: (provider: ProviderSummary) => void };

const addKey = 'providers.add';

type PendingAdd = {
  providerName?: unknown;
  displayName?: unknown;
  category?: unknown;
  agentTypeId?: unknown;
  testUrl?: unknown;
  scheme?: unknown;
  authHeader?: unknown;
};

const schemeLabels: Record<TestAuthScheme, string> = {
  BEARER: 'Authorization: Bearer',
  X_API_KEY: 'X-API-Key header',
  X_GOOG_API_KEY: 'X-Goog-API-Key header',
  HEADER: 'Custom header name',
};

export function AddProviderForm({ onCreated }: Props) {
  const panelId = useId();
  const toggleRef = useRef<HTMLButtonElement>(null);
  const firstFieldRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stepUp, setStepUp] = useState(false);
  const [message, setMessage] = useState<PricingNotice | null>(null);
  const [providerName, setProviderName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [category, setCategory] = useState<ProviderCategory>('PLATFORM_LLM');
  const [agentTypeId, setAgentTypeId] = useState('');
  const [testUrl, setTestUrl] = useState('');
  const [scheme, setScheme] = useState<TestAuthScheme>('BEARER');
  const [authHeader, setAuthHeader] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [signedIn, setSignedIn] = useState(false);

  // Nothing here is a secret, so the form comes back as it was; creating a provider still waits for the person.
  useResumeAfterStepUp<PendingAdd>(addKey, (payload) => {
    if (typeof payload.providerName === 'string') setProviderName(payload.providerName);
    if (typeof payload.displayName === 'string') setDisplayName(payload.displayName);
    if (payload.category === 'PLATFORM_LLM' || payload.category === 'AGENT_API') setCategory(payload.category);
    if (typeof payload.agentTypeId === 'string') setAgentTypeId(payload.agentTypeId);
    if (typeof payload.testUrl === 'string') setTestUrl(payload.testUrl);
    if (typeof payload.scheme === 'string' && payload.scheme in schemeLabels) {
      setScheme(payload.scheme as TestAuthScheme);
    }
    if (typeof payload.authHeader === 'string') setAuthHeader(payload.authHeader);
    setOpen(true);
    setSignedIn(true);
  });

  useEffect(() => {
    if (open) firstFieldRef.current?.focus();
  }, [open]);

  function close() {
    setOpen(false);
    setMessage(null);
    setStepUp(false);
    setSignedIn(false);
    setErrors({});
    toggleRef.current?.focus();
  }

  function validate(): Record<string, string> {
    const found: Record<string, string> = {};
    if (!providerNamePattern.test(providerName)) {
      found.providerName = 'Use 2 to 48 lowercase letters, digits or hyphens.';
    }
    if (displayName.trim().length < 2) found.displayName = 'Enter a display name of at least 2 characters.';
    if (testUrl.trim() !== '' && !/^https:\/\/[^\s/]+/.test(testUrl.trim())) {
      found.testUrl = 'The test address must start with https://.';
    }
    if (testUrl.trim() !== '' && scheme === 'HEADER' && authHeader.trim() === '') {
      found.authHeader = 'Enter the header name the provider expects.';
    }
    return found;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length > 0) {
      setMessage({
        kind: 'error',
        text: 'Fix the highlighted fields and try again.',
      });
      return;
    }
    const body: CreateProviderInput = {
      providerName,
      displayName: displayName.trim(),
      category,
    };
    if (category === 'AGENT_API' && agentTypeId.trim() !== '') body.agentTypeId = agentTypeId.trim();
    if (testUrl.trim() !== '') {
      body.testUrl = testUrl.trim();
      body.testAuthScheme = scheme;
      if (scheme === 'HEADER') body.testAuthHeader = authHeader.trim();
    }
    setBusy(true);
    setMessage(null);
    setStepUp(false);
    setSignedIn(false);
    const result = await providerCall<ProviderSummary>('POST', '', body);
    setBusy(false);
    if (!result.ok) {
      setMessage({ kind: 'error', text: problemText(result.problem) });
      setStepUp(result.problem.code === 'PROVIDER_STEP_UP_REQUIRED');
      return;
    }
    setProviderName('');
    setDisplayName('');
    setAgentTypeId('');
    setTestUrl('');
    setAuthHeader('');
    setOpen(false);
    setMessage(null);
    onCreated(result.data);
  }

  function describedBy(field: string, hintId: string) {
    return errors[field] ? `${hintId} ${hintId}-error` : hintId;
  }

  return (
    <section aria-labelledby={`${panelId}-title`} className="workbench-section providers-add">
      <h2 id={`${panelId}-title`}>Add provider</h2>
      <p className="workbench-hint">
        Register a paid API WAOOAW can use, then enter its value from the provider panel. Only the Founder can do this.
      </p>
      <button
        aria-controls={panelId}
        aria-expanded={open}
        className="primary-command"
        onClick={() => (open ? close() : setOpen(true))}
        ref={toggleRef}
        type="button"
      >
        <Plus aria-hidden="true" size={18} />
        Add provider
      </button>
      {open ? (
        <form className="workbench-form" id={panelId} noValidate onSubmit={(event) => void submit(event)}>
          <label>
            Provider name
            <input
              aria-describedby={describedBy('providerName', `${panelId}-name`)}
              aria-invalid={errors.providerName ? true : undefined}
              autoComplete="off"
              maxLength={48}
              onChange={(event) => setProviderName(event.target.value.toLowerCase())}
              ref={firstFieldRef}
              required
              value={providerName}
            />
          </label>
          <p className="workbench-hint" id={`${panelId}-name`}>
            Lowercase letters, digits and hyphens, for example openai or acme-search.
          </p>
          {errors.providerName ? (
            <p className="error-copy" id={`${panelId}-name-error`}>
              {errors.providerName}
            </p>
          ) : null}
          <label>
            Display name
            <input
              aria-describedby={errors.displayName ? `${panelId}-display-error` : undefined}
              aria-invalid={errors.displayName ? true : undefined}
              autoComplete="off"
              maxLength={80}
              onChange={(event) => setDisplayName(event.target.value)}
              required
              value={displayName}
            />
          </label>
          {errors.displayName ? (
            <p className="error-copy" id={`${panelId}-display-error`}>
              {errors.displayName}
            </p>
          ) : null}
          <label>
            Category
            <select onChange={(event) => setCategory(event.target.value as ProviderCategory)} value={category}>
              <option value="PLATFORM_LLM">Platform API (LLM etc.)</option>
              <option value="AGENT_API">Agent API</option>
            </select>
          </label>
          {category === 'AGENT_API' ? (
            <label>
              Agent type (optional)
              <input
                autoComplete="off"
                maxLength={64}
                onChange={(event) => setAgentTypeId(event.target.value)}
                value={agentTypeId}
              />
            </label>
          ) : null}
          <label>
            Test address (optional, https only)
            <input
              aria-describedby={describedBy('testUrl', `${panelId}-url`)}
              aria-invalid={errors.testUrl ? true : undefined}
              autoComplete="off"
              inputMode="url"
              maxLength={300}
              onChange={(event) => setTestUrl(event.target.value)}
              type="url"
              value={testUrl}
            />
          </label>
          <p className="workbench-hint" id={`${panelId}-url`}>
            A read-only address WAOOAW calls once to check the value. Without it, a value can only be saved after you
            acknowledge it was not tested.
          </p>
          {errors.testUrl ? (
            <p className="error-copy" id={`${panelId}-url-error`}>
              {errors.testUrl}
            </p>
          ) : null}
          {testUrl.trim() !== '' ? (
            <label>
              How the value is sent in the test
              <select onChange={(event) => setScheme(event.target.value as TestAuthScheme)} value={scheme}>
                {(Object.keys(schemeLabels) as TestAuthScheme[]).map((key) => (
                  <option key={key} value={key}>
                    {schemeLabels[key]}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          {testUrl.trim() !== '' && scheme === 'HEADER' ? (
            <label>
              Header name
              <input
                aria-describedby={errors.authHeader ? `${panelId}-header-error` : undefined}
                aria-invalid={errors.authHeader ? true : undefined}
                autoComplete="off"
                maxLength={64}
                onChange={(event) => setAuthHeader(event.target.value)}
                value={authHeader}
              />
            </label>
          ) : null}
          {errors.authHeader ? (
            <p className="error-copy" id={`${panelId}-header-error`}>
              {errors.authHeader}
            </p>
          ) : null}
          <div className="workbench-actions">
            <button className="primary-command" disabled={busy} type="submit">
              {busy ? 'Creating...' : 'Create provider'}
            </button>
            <button className="secondary-link" disabled={busy} onClick={close} type="button">
              Cancel
            </button>
          </div>
        </form>
      ) : null}
      {signedIn ? <output className="workbench-hint">{stepUpSignedInText('Create provider')}</output> : null}
      <PricingMessage message={message} />
      {stepUp ? (
        <StepUpCommand
          payload={{ providerName, displayName, category, agentTypeId, testUrl, scheme, authHeader }}
          pendingKey={addKey}
        />
      ) : null}
    </section>
  );
}
