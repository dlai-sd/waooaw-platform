'use client';

// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R005, WC149-R010
// Constitutional basis: C-023, C-059, C-063, C-083

import { MessageSquareText } from 'lucide-react';
import { useId, useState } from 'react';
import { StepUpCommand } from '@/components/admin/StepUpCommand';
import { PricingMessage, type PricingNotice } from '@/components/admin/pricing/usePricingCommand';
import { providerCall } from '@/lib/provider-admin-call';
import { attemptText, problemText, type ProviderSummary, type TestAnswerResult } from '@/lib/provider-admin-client';
import { stepUpResumingText, useResumeAfterStepUp } from '@/lib/step-up-resume';

type Props = {
  provider: ProviderSummary;
  fallbackCandidates: ProviderSummary[];
};

function figure(value: number | null | undefined, unit: string): string {
  return typeof value === 'number' ? `${value} ${unit}` : 'not reported';
}

export function ProviderTestAnswer({ provider, fallbackCandidates }: Props) {
  const ids = useId();
  const answerKey = `providers.answer.${provider.id}`;
  const [model, setModel] = useState('');
  const [fallbacks, setFallbacks] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<TestAnswerResult | null>(null);
  const [message, setMessage] = useState<PricingNotice | null>(null);
  const [stepUp, setStepUp] = useState(false);

  function toggleFallback(providerName: string, checked: boolean) {
    setFallbacks((current) =>
      checked ? [...current, providerName] : current.filter((entry) => entry !== providerName)
    );
  }

  // The question and the choices are not secret and nothing ran before the step-up, so it asks again on its own.
  const resuming = useResumeAfterStepUp<{ model?: unknown; fallbacks?: unknown }>(answerKey, async (payload) => {
    const chosenModel = typeof payload.model === 'string' ? payload.model : '';
    const chosenFallbacks = Array.isArray(payload.fallbacks)
      ? payload.fallbacks.filter(
          (name): name is string =>
            typeof name === 'string' && fallbackCandidates.some((candidate) => candidate.providerName === name)
        )
      : [];
    setModel(chosenModel);
    setFallbacks(chosenFallbacks);
    await run(chosenModel, chosenFallbacks);
  });

  async function run(modelValue: string, fallbackList: string[]) {
    setBusy(true);
    setMessage(null);
    setStepUp(false);
    setResult(null);
    const trimmed = modelValue.trim();
    const response = await providerCall<TestAnswerResult>('POST', `/${provider.providerName}/test-answer`, {
      model: trimmed.length > 0 ? trimmed : null,
      fallbackProviders: fallbackList,
    });
    if (response.ok) {
      setResult({
        answered: response.data?.answered ?? null,
        attempts: Array.isArray(response.data?.attempts) ? response.data.attempts : [],
      });
    } else {
      const stepUpRequired = response.problem.code === 'PROVIDER_STEP_UP_REQUIRED';
      setMessage({
        kind: 'error',
        text: stepUpRequired
          ? 'Confirm your identity again with multi-factor sign-in. Test answer then runs again on its own.'
          : problemText(response.problem),
      });
      setStepUp(stepUpRequired);
    }
    setBusy(false);
  }

  const answered = result?.answered ?? null;
  return (
    <section aria-labelledby={`${ids}-title`} className="workbench-stack providers-answer">
      <h3 id={`${ids}-title`}>
        <MessageSquareText aria-hidden="true" size={20} /> Test answer
      </h3>
      <p className="workbench-hint">
        Ask the saved {provider.displayName} key a short fixed question through the AI runtime to prove it can really
        answer. No customer data is sent. This uses the active saved version and may cost a small amount.
      </p>
      <div className="workbench-form providers-answer-form">
        <label>
          Model (optional)
          <input
            autoCapitalize="off"
            autoComplete="off"
            disabled={busy}
            maxLength={128}
            onChange={(event) => setModel(event.target.value)}
            spellCheck={false}
            type="text"
            value={model}
          />
        </label>
        {fallbackCandidates.length > 0 ? (
          <fieldset className="providers-fallbacks">
            <legend>Fallback providers (optional)</legend>
            <p className="workbench-hint">If this provider cannot answer, the ticked providers are tried in turn.</p>
            {fallbackCandidates.map((candidate) => (
              <label className="providers-acknowledge" key={candidate.id}>
                <input
                  checked={fallbacks.includes(candidate.providerName)}
                  disabled={busy}
                  onChange={(event) => toggleFallback(candidate.providerName, event.target.checked)}
                  type="checkbox"
                />
                {candidate.displayName}
              </label>
            ))}
          </fieldset>
        ) : null}
        <div className="workbench-actions">
          <button className="secondary-link" disabled={busy} onClick={() => void run(model, fallbacks)} type="button">
            {busy ? 'Asking...' : 'Test answer'}
          </button>
        </div>
      </div>
      <output aria-live="polite" className="providers-answer-result">
        {resuming ? `${stepUpResumingText} ` : null}
        {busy ? 'Waiting for the provider to answer...' : null}
        {result && !busy ? (
          <div className="workbench-stack">
            {answered ? (
              <>
                <p data-outcome="PASSED">
                  <strong>{answered.provider} answered.</strong>
                </p>
                <blockquote className="providers-answer-text">{answered.text}</blockquote>
                <dl className="providers-answer-facts">
                  <div>
                    <dt>Model reported</dt>
                    <dd>{answered.reportedModel ?? answered.model ?? 'not reported'}</dd>
                  </div>
                  <div>
                    <dt>Tokens in</dt>
                    <dd>{figure(answered.inputTokens, 'tokens')}</dd>
                  </div>
                  <div>
                    <dt>Tokens out</dt>
                    <dd>{figure(answered.outputTokens, 'tokens')}</dd>
                  </div>
                  <div>
                    <dt>Latency</dt>
                    <dd>{figure(answered.latencyMs, 'ms')}</dd>
                  </div>
                </dl>
              </>
            ) : (
              <p data-outcome="FAILED">
                <strong>No provider answered.</strong> See why each one was skipped below.
              </p>
            )}
            {result.attempts.length > 0 ? (
              <div>
                <h4>Attempts</h4>
                <ol className="providers-attempts">
                  {result.attempts.map((attempt, index) => (
                    <li key={`${attempt.provider}-${index}`}>
                      <strong>{attempt.provider}</strong>: {attemptText(attempt)}.
                    </li>
                  ))}
                </ol>
              </div>
            ) : null}
          </div>
        ) : null}
      </output>
      <PricingMessage message={message} />
      {stepUp ? <StepUpCommand payload={{ providerId: provider.id, model, fallbacks }} pendingKey={answerKey} /> : null}
    </section>
  );
}
