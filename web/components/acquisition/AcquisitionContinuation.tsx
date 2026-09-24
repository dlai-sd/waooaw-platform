'use client';

// Implements: WC-096 §4.3 Marketplace And Disclosure
// Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { LoaderCircle } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

export type AcquisitionContinuationProps = {
  professionalType: string;
  professionalVersion: string;
  intent: 'trial' | 'hire';
  disclosureRevision: string;
  termsVersion: string;
  idempotencyKey: string;
};

export function AcquisitionContinuation(props: AcquisitionContinuationProps) {
  const router = useRouter();
  const started = useRef(false);
  const [failure, setFailure] = useState<{ retryable: boolean; title: string } | null>(null);

  async function continueAcquisition() {
    setFailure(null);
    try {
      const response = await fetch('/api/acquisition/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(props),
      });
      const result: unknown = await response.json();
      if (!response.ok) {
        const title =
          result && typeof result === 'object' && 'title' in result && typeof result.title === 'string'
            ? result.title
            : undefined;
        throw new AcquisitionResponseError({ status: response.status, title });
      }
      if (
        !result ||
        typeof result !== 'object' ||
        !('resumePath' in result) ||
        typeof result.resumePath !== 'string' ||
        !/^\/relationships\/[0-9a-f-]+$/i.test(result.resumePath)
      )
        throw new Error();
      router.replace(result.resumePath);
    } catch (error) {
      const response = error instanceof AcquisitionResponseError ? error.response : null;
      setFailure({
        retryable: response?.status === 503,
        title: response?.title ?? 'We could not continue yet',
      });
    }
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void continueAcquisition();
    // The accepted continuation is immutable for this mounted return route.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="portal-status" aria-live="polite">
      {failure ? (
        <>
          <h2>{failure.title}</h2>
          <p>This request did not complete cleanly. Check My Agents before making another attempt.</p>
          <div className="command-row">
            {failure.retryable ? (
              <button className="primary-command" onClick={() => void continueAcquisition()} type="button">
                Try same request again
              </button>
            ) : null}
            <Link className="secondary-link" href="/professionals/mine">
              View My Agents
            </Link>
            <Link className="text-command" href="/marketplace">
              Cancel
            </Link>
          </div>
        </>
      ) : (
        <>
          <LoaderCircle aria-hidden="true" className="spin" />
          <p>Preparing your {props.intent === 'trial' ? 'trial' : 'hiring'} workspace...</p>
        </>
      )}
    </section>
  );
}

class AcquisitionResponseError extends Error {
  constructor(readonly response: { status: number; title?: string }) {
    super(response.title);
  }
}
