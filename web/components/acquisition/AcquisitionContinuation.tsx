'use client';

// Implements: WC-096 §4.3 Marketplace And Disclosure
// Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { CircleAlert, LoaderCircle } from 'lucide-react';
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
  couponCode?: string;
};

interface CheckoutOutcome {
  outcome_kind?: string;
  checkout_intent_id?: string;
  provider_order_reference?: string;
  public_checkout_key?: string;
  amount_inr_paise?: number;
  currency?: string;
  merchant_display_name?: string;
  enabled_method_families?: string[];
  resumePath?: string;
  title?: string;
  customer_safe_next_action?: string;
}

interface RazorpayCheckout {
  on(event: 'payment.failed', handler: (response: RazorpayFailureResponse) => void): void;
  open(): void;
}

interface RazorpaySuccessResponse {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

interface RazorpayFailureResponse {
  error?: { description?: string };
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => RazorpayCheckout;
  }
}

const razorpayScriptId = 'razorpay-checkout-script';
const razorpayLogoUrl =
  'https://raw.githubusercontent.com/dlai-sd/waooaw-platform/main/web/public/waooaw-platform-logo.png';

async function loadRazorpayCheckout() {
  if (window.Razorpay) return;
  await new Promise<void>((resolve, reject) => {
    const existing = document.getElementById(razorpayScriptId) as HTMLScriptElement | null;
    const script = existing ?? document.createElement('script');
    script.addEventListener('load', () => resolve(), { once: true });
    script.addEventListener('error', () => reject(new Error('Secure Razorpay Checkout could not be loaded.')), {
      once: true,
    });
    if (!existing) {
      script.id = razorpayScriptId;
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      document.head.appendChild(script);
    }
  });
  if (!window.Razorpay) throw new Error('Secure Razorpay Checkout could not be loaded.');
}

export function AcquisitionContinuation(props: AcquisitionContinuationProps) {
  const router = useRouter();
  const started = useRef(false);
  const [status, setStatus] = useState(
    props.intent === 'trial' ? 'Preparing your trial workspace...' : 'Opening secure Razorpay Checkout...'
  );
  const [busy, setBusy] = useState(true);
  const [retryable, setRetryable] = useState(false);

  async function continueTrial() {
    const response = await fetch('/api/acquisition/continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(props),
    });
    const result = (await response.json().catch(() => ({}))) as CheckoutOutcome & { code?: string };
    if (!response.ok || !result.resumePath) {
      throw new AcquisitionResponseError({ code: result.code, status: response.status, title: result.title });
    }
    router.replace(result.resumePath);
  }

  async function completeRazorpayPayment(response: RazorpaySuccessResponse) {
    setBusy(true);
    setStatus('Razorpay received the payment. WAOOAW is verifying the signed confirmation...');
    const confirmation = await fetch('/api/acquisition/hire-checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...props,
        action: 'confirm',
        razorpayOrderId: response.razorpay_order_id,
        razorpayPaymentId: response.razorpay_payment_id,
        razorpaySignature: response.razorpay_signature,
      }),
    });
    const outcome = (await confirmation.json().catch(() => ({}))) as CheckoutOutcome;
    if (!confirmation.ok || !outcome.resumePath) {
      setStatus(outcome.title ?? 'Payment confirmation is unresolved. Retry to reconcile the same payment.');
      setBusy(false);
      setRetryable(true);
      return;
    }
    router.replace(outcome.resumePath);
  }

  async function startHireCheckout() {
    setBusy(true);
    setRetryable(false);
    setStatus('Opening secure Razorpay Checkout...');
    try {
      const response = await fetch('/api/acquisition/hire-checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...props, action: 'start' }),
      });
      const outcome = (await response.json().catch(() => ({}))) as CheckoutOutcome;
      if (!response.ok) throw new AcquisitionResponseError({ status: response.status, title: outcome.title });
      if (outcome.resumePath) {
        router.replace(outcome.resumePath);
        return;
      }
      if (
        outcome.outcome_kind !== 'RAZORPAY_CHECKOUT_REQUIRED' ||
        !outcome.checkout_intent_id ||
        !outcome.provider_order_reference ||
        !outcome.public_checkout_key ||
        !outcome.amount_inr_paise ||
        outcome.currency !== 'INR' ||
        !outcome.merchant_display_name
      ) {
        setStatus(outcome.customer_safe_next_action ?? 'Secure Razorpay Checkout is not available yet.');
        setBusy(false);
        setRetryable(outcome.outcome_kind === 'OUTCOME_UNRESOLVED');
        return;
      }
      await loadRazorpayCheckout();
      const Checkout = window.Razorpay;
      if (!Checkout) throw new Error('Secure Razorpay Checkout could not be loaded.');
      const checkout = new Checkout({
        key: outcome.public_checkout_key,
        amount: outcome.amount_inr_paise,
        currency: outcome.currency,
        name: outcome.merchant_display_name,
        image: razorpayLogoUrl,
        order_id: outcome.provider_order_reference,
        handler: (payment: RazorpaySuccessResponse) => {
          if (
            payment.razorpay_order_id !== outcome.provider_order_reference ||
            !payment.razorpay_payment_id ||
            !payment.razorpay_signature
          ) {
            setStatus('Razorpay returned an invalid payment confirmation. No Hire was started.');
            setBusy(false);
            setRetryable(true);
            return;
          }
          void completeRazorpayPayment(payment);
        },
        modal: {
          ondismiss: () => {
            setStatus('Razorpay Checkout was closed. No Hire was started.');
            setBusy(false);
            setRetryable(true);
          },
        },
      });
      checkout.on('payment.failed', (failure) => {
        setStatus(failure.error?.description ?? 'Razorpay could not complete the payment. No Hire was started.');
        setBusy(false);
        setRetryable(true);
      });
      checkout.open();
      setStatus('Complete payment in the secure Razorpay window.');
      setBusy(false);
    } catch (error) {
      const response = error instanceof AcquisitionResponseError ? error.response : null;
      setStatus(response?.title ?? (error instanceof Error ? error.message : 'Secure checkout is unavailable.'));
      setBusy(false);
      setRetryable(response?.status === 503);
    }
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (props.intent === 'hire') void startHireCheckout();
    else
      void continueTrial().catch((error) => {
        const response = error instanceof AcquisitionResponseError ? error.response : null;
        setStatus(response?.title ?? 'We could not continue yet.');
        setBusy(false);
        setRetryable(response?.status === 503);
      });
    // The accepted continuation is immutable for this mounted return route.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="portal-status" aria-live="polite">
      {busy ? <LoaderCircle aria-hidden="true" className="spin" /> : <CircleAlert aria-hidden="true" />}
      <h2>{props.intent === 'hire' ? 'Secure payment' : 'Starting your trial'}</h2>
      <p>{status}</p>
      {!busy ? (
        <div className="command-row">
          {retryable ? (
            <button className="primary-command" onClick={() => void startHireCheckout()} type="button">
              Open Razorpay Checkout
            </button>
          ) : null}
          <Link className="text-command" href="/marketplace">
            Cancel
          </Link>
        </div>
      ) : null}
    </section>
  );
}

class AcquisitionResponseError extends Error {
  constructor(readonly response: { code?: string; status: number; title?: string }) {
    super(response.title);
  }
}
