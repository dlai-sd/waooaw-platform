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
  const [failed, setFailed] = useState(false);

  async function continueAcquisition() {
    setFailed(false);
    try {
      const response = await fetch('/api/acquisition/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(props),
      });
      const result = await response.json();
      if (
        !response.ok ||
        typeof result.resumePath !== 'string' ||
        !/^\/relationships\/[0-9a-f-]+$/i.test(result.resumePath)
      )
        throw new Error();
      router.replace(result.resumePath);
    } catch {
      setFailed(true);
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
      {failed ? (
        <>
          <h2>We could not continue yet</h2>
          <p>No trial, contract, payment, or live work was started. You can safely retry the same request.</p>
          <div className="command-row">
            <button className="primary-command" onClick={() => void continueAcquisition()} type="button">
              Try again
            </button>
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
