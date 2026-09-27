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

type HireCommercialPreview = {
  outcome_kind: 'FULLY_DISCOUNTED' | 'PAYMENT_REQUIRED_AFTER_CONTRACT';
  list_price_inr_paise: number;
  discount_inr_paise: number;
  tax_inr_paise: number;
  payable_inr_paise: number;
  currency: 'INR';
  cadence: string;
  coupon_code?: string;
  provider: 'RAZORPAY';
  payment_method_required: boolean;
  renewal_consequence: string;
};

const money = (paise: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(paise / 100);

export function AcquisitionContinuation(props: AcquisitionContinuationProps) {
  const router = useRouter();
  const started = useRef(false);
  const [preview, setPreview] = useState<HireCommercialPreview | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [failure, setFailure] = useState<{
    action?: 'login' | 'register' | 'mine';
    retryable: boolean;
    title: string;
  } | null>(null);

  async function continueAcquisition() {
    setSubmitting(true);
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
        const code =
          result && typeof result === 'object' && 'code' in result && typeof result.code === 'string'
            ? result.code
            : undefined;
        throw new AcquisitionResponseError({ code, status: response.status, title });
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
        action:
          response?.status === 401
            ? 'login'
            : response?.code === 'REGISTRATION_REQUIRED'
              ? 'register'
              : response?.status === 409
                ? 'mine'
                : undefined,
        retryable: response?.status === 503,
        title: response?.title ?? 'We could not continue yet',
      });
      setSubmitting(false);
    }
  }

  async function loadHirePreview() {
    setFailure(null);
    try {
      const response = await fetch('/api/acquisition/hire-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          professionalType: props.professionalType,
          professionalVersion: props.professionalVersion,
        }),
      });
      const result = (await response.json()) as HireCommercialPreview & { title?: string };
      if (!response.ok) throw new AcquisitionResponseError({ status: response.status, title: result.title });
      setPreview(result);
    } catch (error) {
      const response = error instanceof AcquisitionResponseError ? error.response : null;
      setFailure({ retryable: true, title: response?.title ?? 'Payment review is unavailable' });
    }
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (props.intent === 'hire') void loadHirePreview();
    else void continueAcquisition();
    // The accepted continuation is immutable for this mounted return route.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="portal-status" aria-live="polite">
      {failure ? (
        <>
          <h2>{failure.title}</h2>
          <p>
            {failure.retryable
              ? 'The outcome is uncertain. Retry the same request to check it without creating a duplicate.'
              : failure.action === 'mine'
                ? 'The request was not accepted. Check My Agents before making another attempt.'
                : 'The request was not accepted and no professional was started.'}
          </p>
          <div className="command-row">
            {failure.retryable ? (
              <button
                className="primary-command"
                onClick={() => void (props.intent === 'hire' && !preview ? loadHirePreview() : continueAcquisition())}
                type="button"
              >
                Try same request again
              </button>
            ) : null}
            {failure.action === 'login' ? (
              <Link className="secondary-link" href="/login">
                Sign in
              </Link>
            ) : failure.action === 'register' ? (
              <Link className="secondary-link" href="/register">
                Complete registration
              </Link>
            ) : failure.action === 'mine' ? (
              <Link className="secondary-link" href="/professionals/mine">
                View My Agents
              </Link>
            ) : null}
            <Link className="text-command" href="/marketplace">
              Cancel
            </Link>
          </div>
        </>
      ) : preview ? (
        <div className="hire-commercial-review">
          <p className="eyebrow">Payment review</p>
          <h2>Confirm your Hire total</h2>
          <dl className="contract-money">
            <div><dt>Professional plan</dt><dd>{money(preview.list_price_inr_paise)}</dd></div>
            <div><dt>{preview.coupon_code ?? 'Discount'}</dt><dd>-{money(preview.discount_inr_paise)}</dd></div>
            <div><dt>GST included</dt><dd>{money(preview.tax_inr_paise)}</dd></div>
            <div><dt>Amount payable now</dt><dd>{money(preview.payable_inr_paise)}</dd></div>
          </dl>
          <p>
            {preview.payment_method_required
              ? 'Razorpay payment is completed after configuration produces the exact contract.'
              : '100% Demo discount applied. No card, UPI, bank account, wallet, or Razorpay payment is required.'}
          </p>
          <p>{preview.renewal_consequence}</p>
          <div className="command-row">
            <button className="primary-command" disabled={submitting} onClick={() => void continueAcquisition()} type="button">
              {submitting ? 'Starting Hire...' : preview.payable_inr_paise === 0 ? 'Confirm ₹0 Hire' : 'Confirm and configure'}
            </button>
            <Link className="text-command" href="/marketplace">Cancel</Link>
          </div>
        </div>
      ) : (
        <>
          <LoaderCircle aria-hidden="true" className="spin" />
          <p>{props.intent === 'trial' ? 'Preparing your trial workspace...' : 'Preparing your payment review...'}</p>
        </>
      )}
    </section>
  );
}

class AcquisitionResponseError extends Error {
  constructor(readonly response: { code?: string; status: number; title?: string }) {
    super(response.title);
  }
}
