'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';

export interface ContractJourneyProjection {
  contractId: string;
  version: number;
  contractHash: string;
  relationshipState: string;
  acceptanceState: string;
  paymentState: string;
  activationState: string;
  document: {
    professionalDisplayName: string;
    rights: string[];
    obligations: string[];
    limitations: string[];
    authorityTerms: string[];
    stopTerms: string[];
    priceTax: {
      currency: string;
      grossAmountInrPaise: number;
      gstAmountInrPaise: number;
      cadence: string;
      subscriptionTerms: string;
      adSpendTreatment: string;
      cancellationAndRefundTerms: string;
      offeringId?: string;
      bundleTier?: string;
      quoteVersion?: string;
      renewalConsequence?: string;
    };
  };
}

interface CheckoutOutcome {
  outcomeKind: 'RAZORPAY_CHECKOUT_REQUIRED' | 'CAPTURED' | 'FULLY_DISCOUNTED' | 'PROVIDER_CONFIGURATION_PENDING' | 'COMMERCIAL_CONFLICT' | 'OUTCOME_UNRESOLVED';
  checkoutIntentId?: string;
  providerOrderReference?: string;
  publicCheckoutKey?: string;
  amountInrPaise?: number;
  currency?: string;
  merchantDisplayName?: string;
  enabledMethodFamilies?: string[];
  expiresAt?: string;
  payableInrPaise?: number;
  listPriceInrPaise?: number;
  discountInrPaise?: number;
  taxInrPaise?: number;
  renewalConsequence?: string;
  commercialOutcomeReference?: string;
  commercialEvidenceId?: string;
  reasonCode?: string;
  customerSafeNextAction?: string;
}

interface RazorpayCheckout {
  open(): void;
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => RazorpayCheckout;
  }
}

interface Props { relationshipId: string; journey: ContractJourneyProjection | null }

const money = (paise: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(paise / 100);
const razorpayScriptId = 'razorpay-checkout-script';

async function loadRazorpayCheckout() {
  if (window.Razorpay) return;
  await new Promise<void>((resolve, reject) => {
    const existing = document.getElementById(razorpayScriptId) as HTMLScriptElement | null;
    const script = existing ?? document.createElement('script');
    script.addEventListener('load', () => resolve(), { once: true });
    script.addEventListener('error', () => reject(new Error('Secure Razorpay Checkout could not be loaded.')), { once: true });
    if (!existing) {
      script.id = razorpayScriptId;
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      document.head.appendChild(script);
    }
  });
  if (!window.Razorpay) throw new Error('Secure Razorpay Checkout could not be loaded.');
}
const newIdempotencyKey = () => {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
};

export function ContractJourney({ relationshipId, journey }: Props) {
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState(journey?.acceptanceState === 'ACCEPTED');
  const [checkout, setCheckout] = useState<CheckoutOutcome | null>(null);
  const idempotencyKeys = useRef<Record<string, string>>({});
  if (!journey) return null;

  async function reconcileCheckout(checkoutIntentId: string) {
    setStatus('Payment confirmation is being reconciled with Razorpay.');
    const response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/contract-journey?checkoutIntentId=${encodeURIComponent(checkoutIntentId)}`, { cache: 'no-store' });
    const result = await response.json().catch(() => ({})) as CheckoutOutcome & { title?: string };
    if (!response.ok) {
      setStatus(result.title ?? 'Payment confirmation remains unresolved. No activation success was recorded.');
      return;
    }
    setCheckout(result);
    setStatus(result.outcomeKind === 'CAPTURED'
      ? 'Payment captured and reconciled by WAOOAW. Activation is ready for your confirmation.'
      : result.customerSafeNextAction ?? 'Payment confirmation remains pending. Do not create another order.');
  }

  async function launchRazorpay(outcome: CheckoutOutcome) {
    if (!outcome.checkoutIntentId || !outcome.publicCheckoutKey || !outcome.providerOrderReference
      || !outcome.amountInrPaise || outcome.currency !== 'INR' || !outcome.merchantDisplayName) {
      setStatus('Secure Razorpay Checkout configuration is incomplete. No payment was started.');
      return;
    }
    try {
      await loadRazorpayCheckout();
      const Checkout = window.Razorpay!;
      new Checkout({
        key: outcome.publicCheckoutKey,
        amount: outcome.amountInrPaise,
        currency: outcome.currency,
        name: outcome.merchantDisplayName,
        order_id: outcome.providerOrderReference,
        handler: () => void reconcileCheckout(outcome.checkoutIntentId!),
        modal: { ondismiss: () => setStatus('Razorpay Checkout was closed. Payment is not marked failed; reconciliation remains available.') },
        retry: { enabled: false },
      }).open();
    } catch (caught) {
      setStatus(caught instanceof Error ? caught.message : 'Secure Razorpay Checkout could not be loaded.');
    }
  }

  async function command(action: 'accept' | 'pay' | 'activate') {
    setBusy(true);
    setStatus('');
    const response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/contract-journey`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action,
        version: journey!.version,
        contractHash: journey!.contractHash,
        idempotencyKey: idempotencyKeys.current[action] ??= newIdempotencyKey(),
        commercialOutcomeKind: checkout?.outcomeKind === 'FULLY_DISCOUNTED' ? 'ZERO_PRICE_SATISFIED' : undefined,
        ...(checkout?.outcomeKind === 'CAPTURED' ? { commercialOutcomeKind: 'CAPTURED' } : {}),
        commercialOutcomeReference: checkout?.commercialOutcomeReference,
        commercialEvidenceId: checkout?.commercialEvidenceId,
      }),
    });
    const result = await response.json().catch(() => ({}));
    if (response.ok && action === 'accept') {
      setAccepted(true);
      setStatus('Contract accepted and evidenced. Payment has not started.');
    } else if (response.ok && action === 'pay') {
      const outcome = result as CheckoutOutcome;
      setCheckout(outcome);
      if (outcome.outcomeKind === 'RAZORPAY_CHECKOUT_REQUIRED') {
        setStatus('Secure Razorpay Checkout is ready. Payment remains unconfirmed until server reconciliation.');
        await launchRazorpay(outcome);
      } else if (outcome.outcomeKind === 'FULLY_DISCOUNTED') {
        setStatus('100% Demo discount applied. Amount paid: INR 0. No payment method charged.');
      } else {
        setStatus(outcome.customerSafeNextAction ?? 'Checkout remains unresolved. No payment or activation success was recorded.');
      }
    } else if (response.ok) {
      setStatus(checkout?.outcomeKind === 'FULLY_DISCOUNTED'
        ? 'Employment relationship activated. Amount paid: INR 0.'
        : 'Employment relationship activated after reconciled payment.');
    } else {
      setStatus(result.title ?? 'The request remains unresolved. No success was recorded.');
    }
    setBusy(false);
  }

  const terms = journey.document.priceTax;
  return (
    <section className="contract-journey" aria-labelledby="contract-journey-title">
      <div className="contract-heading"><div><p className="section-label">Hire decision</p><h2 id="contract-journey-title">Employment contract</h2></div><span className="currency-state">Version {journey.version}</span></div>
      <p className="contract-hash">Exact contract <code>{journey.contractHash}</code></p>
      <dl className="contract-money">
        <div><dt>Total</dt><dd>{money(terms.grossAmountInrPaise)}</dd></div>
        <div><dt>GST included</dt><dd>{money(terms.gstAmountInrPaise)}</dd></div>
        <div><dt>Wallet seed</dt><dd>{money(0)}</dd></div>
        <div><dt>Cadence</dt><dd>{terms.cadence.toLowerCase()}</dd></div>
        <div><dt>Payment</dt><dd>{journey.paymentState.replaceAll('_', ' ').toLowerCase()}</dd></div>
        <div><dt>Acceptance</dt><dd>{accepted ? 'accepted' : 'pending'}</dd></div>
        <div><dt>Activation</dt><dd>{journey.activationState.replaceAll('_', ' ').toLowerCase()}</dd></div>
      </dl>
      <div className="contract-terms">
        <div><h3>Your rights</h3><ul>{journey.document.rights.map((item) => <li key={item}>{item}</li>)}</ul></div>
        <div><h3>Limits</h3><ul>{journey.document.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div>
      </div>
      <p><strong>Subscription:</strong> {terms.subscriptionTerms}. The full contract total is the subscription amount.</p>
      <p><strong>Ad spend:</strong> {terms.adSpendTreatment}</p>
      <p><strong>Cancellation and refund:</strong> {terms.cancellationAndRefundTerms}</p>
      {checkout?.outcomeKind === 'FULLY_DISCOUNTED' && (
        <section className="discounted-checkout" aria-labelledby="discounted-checkout-title">
          <h3 id="discounted-checkout-title">Payment summary</h3>
          <dl className="contract-money">
            <div><dt>List price</dt><dd>{money(checkout.listPriceInrPaise ?? terms.grossAmountInrPaise)}</dd></div>
            <div><dt>Demo discount</dt><dd>-{money(checkout.discountInrPaise ?? terms.grossAmountInrPaise)}</dd></div>
            <div><dt>Amount paid</dt><dd>INR 0</dd></div>
          </dl>
          <p>{checkout.renewalConsequence ?? terms.renewalConsequence}</p>
          <ul className="payment-method-gallery" aria-label="Payment methods not required">
            {['Credit card', 'Debit card', 'UPI', 'Netbanking', 'Wallet'].map((method) => (
              <li key={method}><strong>{method}</strong><span>Not required - 100% Demo discount applied</span></li>
            ))}
          </ul>
          <p>No bank, card network, UPI app, wallet, or Razorpay processed money.</p>
          <button
            type="button"
            disabled={busy || !checkout.commercialOutcomeReference || !checkout.commercialEvidenceId}
            onClick={() => command('activate')}
          >Complete fully discounted activation</button>
        </section>
      )}
      {checkout?.outcomeKind === 'CAPTURED' && (
        <section className="discounted-checkout" aria-labelledby="captured-checkout-title">
          <h3 id="captured-checkout-title">Payment captured</h3>
          <p>Razorpay payment was signature-verified and reconciled by WAOOAW. Payment capture does not activate the relationship by itself.</p>
          <button
            type="button"
            disabled={busy || !checkout.commercialOutcomeReference || !checkout.commercialEvidenceId}
            onClick={() => command('activate')}
          >Complete paid activation</button>
        </section>
      )}
      <div className="decision-actions" role="group" aria-label="Contract decisions">
        {!accepted && <button type="button" disabled={busy} onClick={() => command('accept')}>Hire and accept exact contract</button>}
        {accepted && journey.activationState !== 'ACTIVE' && <button type="button" disabled={busy} onClick={() => command('pay')}>Continue to payment</button>}
        <button type="button" disabled={busy} onClick={() => setStatus('Not now selected. No contract or payment state changed.')}>Not now</button>
        <button type="button" disabled={busy} onClick={() => setStatus('Cancelled. No contract or payment state changed.')}>Cancel</button>
        <Link href="/home">Exit</Link>
      </div>
      <p className="decision-status" role="status">{status}</p>
      <p className="provider-boundary">Payment details are entered only on Razorpay. WhatsApp and WAOOAW never collect card, UPI, or banking secrets.</p>
    </section>
  );
}
