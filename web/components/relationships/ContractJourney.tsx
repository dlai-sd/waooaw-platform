'use client';

import { useRef, useState } from 'react';

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
    };
  };
}

interface Props { relationshipId: string; journey: ContractJourneyProjection | null }

const money = (paise: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(paise / 100);
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
  const idempotencyKeys = useRef<Record<string, string>>({});
  if (!journey) return null;

  async function command(action: 'accept' | 'pay') {
    setBusy(true);
    setStatus('');
    const response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/contract-journey`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, version: journey!.version, contractHash: journey!.contractHash, grossAmountInrPaise: journey!.document.priceTax.grossAmountInrPaise, idempotencyKey: idempotencyKeys.current[action] ??= newIdempotencyKey() }),
    });
    const result = await response.json().catch(() => ({}));
    if (response.ok && action === 'accept') {
      setAccepted(true);
      setStatus('Contract accepted and evidenced. Payment has not started.');
    } else if (response.ok) {
      setStatus(`Razorpay order ${result.orderId ?? ''} is ready. Payment remains unconfirmed until hosted checkout capture.`);
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
      <div className="decision-actions" role="group" aria-label="Contract decisions">
        {!accepted && <button type="button" disabled={busy} onClick={() => command('accept')}>Hire and accept exact contract</button>}
        {accepted && journey.activationState !== 'ACTIVE' && <button type="button" disabled={busy} onClick={() => command('pay')}>Proceed to Razorpay</button>}
        <button type="button" disabled={busy} onClick={() => setStatus('Not now selected. No contract or payment state changed.')}>Not now</button>
        <button type="button" disabled={busy} onClick={() => setStatus('Cancelled. No contract or payment state changed.')}>Cancel</button>
        <a href="/home">Exit</a>
      </div>
      <p className="decision-status" role="status">{status}</p>
      <p className="provider-boundary">Payment details are entered only on Razorpay. WhatsApp and WAOOAW never collect card, UPI, or banking secrets.</p>
    </section>
  );
}
