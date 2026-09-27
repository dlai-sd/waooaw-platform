'use client';

// Implements: WC-096 §4.3 Marketplace And Disclosure
// Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { CheckCircle2, CreditCard, Landmark, LoaderCircle, QrCode, ShieldCheck, Tag, WalletCards, X } from 'lucide-react';
import Image from 'next/image';
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
  payments_enabled: boolean;
  renewal_consequence: string;
};

const couponValidationMessages: Record<string, string> = {
  COUPON_NOT_FOUND: 'We could not find that coupon. Check the code and try again.',
  COUPON_EXPIRED: 'That coupon has expired. Please try another coupon.',
  COUPON_USED: 'That coupon has reached its usage limit. Please try another coupon.',
  COUPON_AGENT_MISMATCH: 'That coupon is not available for this professional. Please try another coupon.',
  COUPON_TIER_MISMATCH: 'That coupon is not available for this plan. Please try another coupon.',
  DISCOUNT_EXCEEDS_CAP: 'That coupon cannot be applied under the current discount policy.',
};

const paymentsUnavailableMessage =
  'Great news! Hiring is free of charge in the Demo / UAT environment, so no card, UPI, bank, or wallet details are needed. Thank you for choosing WAOOAW, and we wish your business every success.';

const money = (paise: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(paise / 100);

const paymentMethods = [
  { id: 'card', label: 'Card', detail: 'Visa, Mastercard, RuPay and more', icon: CreditCard },
  { id: 'upi', label: 'UPI / QR', detail: 'Any supported UPI app', icon: QrCode },
  { id: 'netbanking', label: 'Netbanking', detail: 'All major Indian banks', icon: Landmark },
  { id: 'wallet', label: 'Wallet', detail: 'Supported digital wallets', icon: WalletCards },
] as const;

export function AcquisitionContinuation(props: AcquisitionContinuationProps) {
  const router = useRouter();
  const started = useRef(false);
  const [preview, setPreview] = useState<HireCommercialPreview | null>(null);
  const [basePreview, setBasePreview] = useState<HireCommercialPreview | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<(typeof paymentMethods)[number]['id']>('upi');
  const [couponCode, setCouponCode] = useState('');
  const [couponError, setCouponError] = useState<string | null>(null);
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

  async function loadHirePreview(code?: string) {
    setFailure(null);
    setCouponError(null);
    try {
      const response = await fetch('/api/acquisition/hire-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          professionalType: props.professionalType,
          professionalVersion: props.professionalVersion,
          ...(code ? { couponCode: code } : {}),
        }),
      });
      const result = (await response.json()) as HireCommercialPreview & {
        detail?: { code?: string };
        title?: string;
      };
      if (!response.ok) {
        if (code && response.status === 422) {
          if (basePreview) setPreview(basePreview);
          const errorCode = result.detail?.code;
          setCouponError(
            errorCode && couponValidationMessages[errorCode]
              ? couponValidationMessages[errorCode]
              : 'We could not apply that coupon. Check the code and try again.'
          );
          return;
        }
        throw new AcquisitionResponseError({ status: response.status, title: result.title });
      }
      setPreview(result);
      if (!code) setBasePreview(result);
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
        <div className="checkout-backdrop">
          <section aria-labelledby="hire-checkout-title" aria-modal="true" className="hire-checkout" role="dialog">
            <header className="hire-checkout-header">
              <div className="checkout-brand-mark">
                <Image alt="WAOOAW" height={32} priority src="/waooaw-platform-logo.png" width={32} />
              </div>
              <div>
                <p>WAOOAW Secure Checkout</p>
                <span><ShieldCheck aria-hidden="true" size={15} /> Razorpay payment options</span>
              </div>
              <Link aria-label="Close checkout" className="checkout-close" href="/marketplace">
                <X aria-hidden="true" size={22} />
              </Link>
            </header>

            <div className="hire-checkout-body">
              <aside className="checkout-order-summary" aria-label="Order summary">
                <p className="eyebrow">Professional Hire</p>
                <h2 id="hire-checkout-title">Complete your checkout</h2>
                <dl>
                  <div><dt>Professional plan</dt><dd>{money(preview.list_price_inr_paise)}</dd></div>
                  <div className="checkout-coupon-row">
                    <dt><Tag aria-hidden="true" size={16} /> {preview.coupon_code ?? 'Discount'}</dt>
                    <dd>-{money(preview.discount_inr_paise)}</dd>
                  </div>
                  <div><dt>GST included</dt><dd>{money(preview.tax_inr_paise)}</dd></div>
                  <div className="checkout-total"><dt>Total due now</dt><dd>{money(preview.payable_inr_paise)}</dd></div>
                </dl>
                {preview.payable_inr_paise === 0 ? (
                  <p className="checkout-discount-state">
                    <CheckCircle2 aria-hidden="true" size={18} /> 100% Demo discount applied
                  </p>
                ) : null}
                <p className="checkout-renewal">{preview.renewal_consequence}</p>
              </aside>

              <div className="checkout-payment-panel">
                <div className="checkout-payment-heading">
                  <div>
                    <p className="eyebrow">Payment methods</p>
                    <h3>{preview.payment_method_required ? 'Choose how to pay' : 'No payment method required'}</h3>
                  </div>
                  <span className="checkout-provider">Secured by Razorpay</span>
                </div>
                <div className="checkout-coupon-control">
                  <label htmlFor="hire-coupon">Discount coupon</label>
                  <div>
                    <Tag aria-hidden="true" size={18} />
                    <input
                      id="hire-coupon"
                      onChange={(event) => {
                        const nextCode = event.target.value.toUpperCase();
                        setCouponCode(nextCode);
                        setCouponError(null);
                        if (preview.coupon_code && preview.coupon_code !== nextCode.trim() && basePreview) {
                          setPreview(basePreview);
                        }
                      }}
                      placeholder="Enter coupon code"
                      value={couponCode}
                    />
                    <button
                      disabled={!couponCode.trim() || submitting}
                      onClick={() => void loadHirePreview(couponCode.trim())}
                      type="button"
                    >
                      {preview.coupon_code === couponCode.trim() ? (
                        <><CheckCircle2 aria-hidden="true" size={16} /> Applied</>
                      ) : 'Apply'}
                    </button>
                  </div>
                  {couponError && couponError !== paymentsUnavailableMessage ? (
                    <p className="checkout-inline-error" role="alert">{couponError}</p>
                  ) : null}
                </div>
                <fieldset className="checkout-methods">
                  <legend>Available payment methods</legend>
                  {paymentMethods.map((method) => {
                    const Icon = method.icon;
                    return (
                      <label key={method.id} className={selectedMethod === method.id ? 'selected' : undefined}>
                        <input
                          checked={selectedMethod === method.id}
                          name="paymentMethod"
                          onChange={() => setSelectedMethod(method.id)}
                          type="radio"
                          value={method.id}
                        />
                        <Icon aria-hidden="true" size={22} />
                        <span><strong>{method.label}</strong><small>{method.detail}</small></span>
                        {selectedMethod === method.id ? <CheckCircle2 aria-hidden="true" size={18} /> : null}
                      </label>
                    );
                  })}
                </fieldset>
                <div className="checkout-method-note">
                  {preview.payable_inr_paise === 0
                    ? `Congratulations! ${preview.coupon_code ?? 'Your coupon'} gives you 100% off this hire. No payment details are needed today. We wish you great business success with your WAOOAW professional!`
                    : 'Payment methods will be enabled when payments are available.'}
                </div>
                {couponError === paymentsUnavailableMessage ? (
                  <p className="checkout-inline-error checkout-payment-error" role="alert">{couponError}</p>
                ) : null}
                <footer className="checkout-actions">
                  <div><span>Amount payable</span><strong>{money(preview.payable_inr_paise)}</strong></div>
                  <button className="primary-command" disabled={submitting} onClick={() => {
                    if (preview.payable_inr_paise > 0 && !preview.payments_enabled) {
                      setCouponError(paymentsUnavailableMessage);
                      return;
                    }
                    void continueAcquisition();
                  }} type="button">
                    {submitting ? 'Starting Hire...' : 'Continue'}
                  </button>
                </footer>
              </div>
            </div>
          </section>
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
