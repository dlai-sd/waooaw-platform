'use client';

// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R003, WC148-R004, WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { CircleCheck, CircleMinus, CircleX, KeyRound } from 'lucide-react';
import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import { PricingMessage, type PricingNotice } from '@/components/admin/pricing/usePricingCommand';
import { providerCall } from '@/lib/provider-admin-call';
import {
  categoryHeadings,
  outcomeLabel,
  problemText,
  type CredentialTestResult,
  type CredentialVersion,
  type ProviderSummary,
  type SavedVersion,
} from '@/lib/provider-admin-client';
import { stepUpSignedInText, useResumeAfterStepUp } from '@/lib/step-up-resume';
import { ProviderHistory, type HistoryState } from './ProviderHistory';
import { ProviderStatusChips } from './ProviderList';
import { ProviderTestAnswer } from './ProviderTestAnswer';

type Props = {
  provider: ProviderSummary;
  fallbackCandidates?: ProviderSummary[];
  focusOnMount: boolean;
  onChanged: () => void;
};

const valueHints: Record<string, string> = {
  meta: 'For Meta, enter the secret value as JSON: {"appId":"...","appSecret":"..."}.',
  sarvam:
    'For Sarvam, Test sends an empty request and treats a validation response as proof that the key is valid; it does not run a real completion.',
};

const outcomeIcon = {
  PASSED: CircleCheck,
  FAILED: CircleX,
  NOT_TESTABLE: CircleMinus,
} as const;

export function ProviderPanel({ provider, fallbackCandidates = [], focusOnMount, onChanged }: Props) {
  const ids = useId();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const valueRef = useRef<HTMLInputElement>(null);
  const testRef = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef<'value' | 'test' | null>(null);
  const [value, setValue] = useState('');
  const [test, setTest] = useState<CredentialTestResult | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState<'test' | 'save' | null>(null);
  const [message, setMessage] = useState<PricingNotice | null>(null);
  const [stepUp, setStepUp] = useState<'test' | 'save' | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [history, setHistory] = useState<HistoryState>({ kind: 'loading' });

  const loadHistory = useCallback(async () => {
    setHistory({ kind: 'loading' });
    const result = await providerCall<CredentialVersion[]>('GET', `/${provider.id}/credentials`);
    setHistory(
      result.ok
        ? { kind: 'ready', versions: result.data }
        : {
            kind: 'error',
            text: `Version history could not be loaded. ${problemText(result.problem)}`,
          }
    );
  }, [provider.id]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (focusOnMount) headingRef.current?.focus();
  }, [focusOnMount]);

  // The value typed before the step-up is never kept, so only a reminder comes back, not an automatic retry.
  useResumeAfterStepUp(`providers.panel.${provider.id}`, () => {
    setSignedIn(true);
    valueRef.current?.focus();
  });

  useEffect(() => {
    if (busy !== null || restoreFocus.current === null) return;
    const target = restoreFocus.current === 'value' ? valueRef : testRef;
    restoreFocus.current = null;
    target.current?.focus();
  }, [busy]);

  function changeValue(next: string) {
    setValue(next);
    setTest(null);
    setAcknowledged(false);
  }

  function discardValue() {
    setValue('');
    setTest(null);
    setAcknowledged(false);
  }

  const testPassed = test?.outcome === 'PASSED';
  const untestedAccepted = test?.outcome === 'NOT_TESTABLE' && acknowledged;
  const canSave = value.length > 0 && busy === null && (testPassed || untestedAccepted);

  async function runTest() {
    setBusy('test');
    setMessage(null);
    setStepUp(null);
    setSignedIn(false);
    restoreFocus.current = 'test';
    const result = await providerCall<CredentialTestResult>('POST', `/${provider.id}/credentials/test`, { value });
    if (!result.ok) {
      discardValue();
      setMessage({ kind: 'error', text: problemText(result.problem) });
      setStepUp(result.problem.code === 'PROVIDER_STEP_UP_REQUIRED' ? 'test' : null);
      restoreFocus.current = 'value';
    } else if (result.data.outcome === 'FAILED') {
      setTest(result.data);
      setValue('');
      restoreFocus.current = 'value';
    } else {
      setTest(result.data);
    }
    setBusy(null);
  }

  async function confirmAndSave() {
    setBusy('save');
    setMessage(null);
    setStepUp(null);
    setSignedIn(false);
    restoreFocus.current = 'value';
    const body: { value: string; acknowledgeUntested?: boolean } = { value };
    if (untestedAccepted) body.acknowledgeUntested = true;
    const result = await providerCall<SavedVersion>('POST', `/${provider.id}/credentials`, body);
    discardValue();
    if (result.ok) {
      setMessage({
        kind: 'success',
        text: `Saved as version ${result.data.versionNo} and active now. The value is not shown again and cannot be read back.`,
      });
      onChanged();
      void loadHistory();
    } else {
      setMessage({ kind: 'error', text: problemText(result.problem) });
      setStepUp(result.problem.code === 'PROVIDER_STEP_UP_REQUIRED' ? 'save' : null);
    }
    setBusy(null);
  }

  function rolledBack(version: SavedVersion) {
    setMessage({
      kind: 'success',
      text: `Rolled back. Version ${version.versionNo} is active now and WAOOAW uses it without a deployment.`,
    });
    onChanged();
    void loadHistory().then(() => headingRef.current?.focus());
  }

  const Icon = test ? outcomeIcon[test.outcome] : null;
  return (
    <section aria-labelledby={`${ids}-title`} className="workbench-section providers-panel">
      <header className="providers-panel-heading">
        <KeyRound aria-hidden="true" size={24} />
        <div>
          <p className="eyebrow">{categoryHeadings[provider.category]}</p>
          <h2 id={`${ids}-title`} ref={headingRef} tabIndex={-1}>
            {provider.displayName}
          </h2>
          <p className="workbench-hint">
            {provider.providerName} · {provider.hasTestEndpoint ? 'Has a test endpoint' : 'No test endpoint'}
          </p>
          <ProviderStatusChips provider={provider} />
        </div>
      </header>

      <fieldset className="workbench-form providers-value">
        <legend id={`${ids}-value-title`}>Enter a new value</legend>
        <label>
          API key or secret value
          <input
            aria-describedby={`${ids}-value-hint`}
            autoCapitalize="off"
            autoComplete="new-password"
            autoCorrect="off"
            disabled={busy !== null}
            maxLength={8192}
            onChange={(event) => changeValue(event.target.value)}
            ref={valueRef}
            spellCheck={false}
            type="password"
            value={value}
          />
        </label>
        <p className="workbench-hint" id={`${ids}-value-hint`}>
          The value goes straight to the secret store. It can never be read back, not by you and not on this page, so
          keep your own copy. Test it first; Confirm and save is enabled only after the latest test of what you typed
          passes.
        </p>
        {valueHints[provider.providerName] ? (
          <p className="workbench-hint" data-testid="provider-value-format">
            {valueHints[provider.providerName]}
          </p>
        ) : null}
        <div className="workbench-actions">
          <button
            className="secondary-link"
            disabled={value.length === 0 || busy !== null}
            onClick={() => void runTest()}
            ref={testRef}
            type="button"
          >
            {busy === 'test' ? 'Testing...' : 'Test'}
          </button>
          <button className="primary-command" disabled={!canSave} onClick={() => void confirmAndSave()} type="button">
            {busy === 'save' ? 'Saving...' : 'Confirm and save'}
          </button>
        </div>
        <output aria-live="polite" className="providers-test-result">
          {test && Icon ? (
            <p data-outcome={test.outcome}>
              <Icon aria-hidden="true" size={18} />
              <strong>{outcomeLabel[test.outcome]}.</strong> {test.detail}
              {typeof test.httpStatus === 'number' ? ` (HTTP ${test.httpStatus})` : ''}
            </p>
          ) : null}
        </output>
        {test?.outcome === 'NOT_TESTABLE' ? (
          <label className="providers-acknowledge">
            <input checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} type="checkbox" />
            Save without a test. I understand this value has not been checked against the provider.
          </label>
        ) : null}
        {signedIn ? (
          <output className="workbench-hint">
            {stepUpSignedInText('Test')} The value was not kept; enter it again first.
          </output>
        ) : null}
        <PricingMessage message={message} />
        {stepUp ? (
          <StepUpCommand
            payload={{ providerId: provider.id, action: stepUp }}
            pendingKey={`providers.panel.${provider.id}`}
          />
        ) : null}
      </fieldset>

      {provider.credential.status === 'ACTIVE' ? (
        <ProviderTestAnswer fallbackCandidates={fallbackCandidates} provider={provider} />
      ) : null}

      <div className="workbench-stack">
        <h3>Version history</h3>
        <ProviderHistory
          history={history}
          onReload={() => void loadHistory()}
          onRolledBack={rolledBack}
          provider={provider}
        />
      </div>
    </section>
  );
}
