'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { useCallback, useState } from 'react';
import { pricingCall } from '@/lib/pricing-admin-call';
import {
  problemText,
  type PricingProblem,
  type PricingResult,
  type PricingViolation,
} from '@/lib/pricing-admin-client';

export type PricingNotice = { kind: 'success' | 'error'; text: string; violations?: PricingViolation[] };

export function usePricingCommand() {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<PricingNotice | null>(null);

  const run = useCallback(
    async <T,>(
      method: 'GET' | 'POST' | 'PUT',
      path: string,
      body?: unknown,
      successText?: string
    ): Promise<PricingResult<T>> => {
      setBusy(true);
      setMessage(null);
      const result = await pricingCall<T>(method, path, body);
      if (result.ok) {
        if (successText) setMessage({ kind: 'success', text: successText });
      } else {
        const problem: PricingProblem = result.problem;
        setMessage({ kind: 'error', text: problemText(problem), violations: problem.violations });
      }
      setBusy(false);
      return result;
    },
    []
  );

  return { busy, message, run, setMessage };
}

export function PricingMessage({ message }: { message: PricingNotice | null }) {
  if (message === null) return <p aria-live="polite" className="workbench-message" />;
  const failed = message.kind === 'error';
  return (
    <div
      aria-live={failed ? 'assertive' : 'polite'}
      className={`workbench-message workbench-message-${message.kind}`}
      role={failed ? 'alert' : 'status'}
    >
      <p>
        <strong>{failed ? 'Error:' : 'Done:'}</strong> {message.text}
      </p>
      {message.violations && message.violations.length > 0 ? (
        <ul className="workbench-plain-list">
          {message.violations.map((violation) => (
            <li key={`${violation.code}:${violation.path}`}>
              {violation.path ? `${violation.path}: ` : ''}
              {violation.message}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
