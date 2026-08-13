'use client';

// Implements: WC-065 WC065-05 Founder decision experience
// Constitutional basis: C-023, C-049, C-059, C-063

import { AlertTriangle, CheckCircle2, LoaderCircle, Scale } from 'lucide-react';
import { FormEvent, useRef, useState } from 'react';
import type { RelationshipOfferabilityDecision } from '@/lib/api/generated/models/RelationshipOfferabilityDecision';

const formatMoney = (paise: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(paise / 100);

export function OfferabilityWorkbench() {
  const [decision, setDecision] = useState<RelationshipOfferabilityDecision | null>(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const idempotencyKey = useRef<string | null>(null);

  async function evaluate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError('');
    setDecision(null);
    const data = new FormData(event.currentTarget);
    const proposedPricePaise = Math.round(Number(data.get('priceRupees')) * 100);
    idempotencyKey.current ??= crypto.randomUUID();
    try {
      const response = await fetch('/api/offerability', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idempotencyKey: idempotencyKey.current,
          relationshipId: data.get('relationshipId'),
          offeringId: data.get('offeringId'),
          agentType: data.get('agentType'),
          bundleTier: data.get('bundleTier'),
          proposedPricePaise,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.code ?? 'OFFERABILITY_UNAVAILABLE');
      setDecision(payload as RelationshipOfferabilityDecision);
      idempotencyKey.current = null;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'OFFERABILITY_UNAVAILABLE');
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="offerability-workbench">
      <header className="offerability-heading">
        <p className="eyebrow">Founder decision</p>
        <h1>Offerability</h1>
        <p>Price one approved professional offering against current owner evidence.</p>
      </header>

      <form className="offerability-form" onSubmit={evaluate} onChange={() => { idempotencyKey.current = null; }}>
        <label>
          Relationship ID
          <input name="relationshipId" type="text" inputMode="text" required />
        </label>
        <label>
          Offering ID
          <input name="offeringId" type="text" defaultValue="dma-starter-v1" required maxLength={128} />
        </label>
        <label>
          Professional type
          <input name="agentType" type="text" defaultValue="DMA" required maxLength={50} />
        </label>
        <label>
          Bundle tier
          <select name="bundleTier" defaultValue="STARTER">
            <option value="STARTER">Starter</option>
            <option value="PRO">Pro</option>
            <option value="ENTERPRISE">Enterprise</option>
          </select>
        </label>
        <label className="offerability-price">
          Customer price (INR)
          <input name="priceRupees" type="number" min="0.01" step="0.01" required />
        </label>
        <button className="primary-command" type="submit" disabled={pending}>
          {pending ? <LoaderCircle className="spin" aria-hidden="true" size={18} /> : <Scale aria-hidden="true" size={18} />}
          {pending ? 'Evaluating' : 'Evaluate offer'}
        </button>
      </form>

      <section className="offerability-result" aria-live="polite">
        {error ? (
          <div className="offerability-failure" role="alert">
            <AlertTriangle aria-hidden="true" size={24} />
            <div><strong>Decision unavailable</strong><p>{error.replaceAll('_', ' ')}</p></div>
          </div>
        ) : null}
        {decision ? (
          <div className={`offerability-decision disposition-${decision.disposition.toLowerCase()}`}>
            {decision.disposition === 'ALLOW' ? <CheckCircle2 aria-hidden="true" size={28} /> : <AlertTriangle aria-hidden="true" size={28} />}
            <div>
              <p className="decision-label">{decision.disposition}</p>
              <h2>{formatMoney(decision.directContributionPaise)} direct contribution</h2>
              {decision.reasons.length ? <ul>{decision.reasons.map((reason) => <li key={reason}>{reason.replaceAll('_', ' ')}</li>)}</ul> : <p>No blocking conditions.</p>}
              <dl>
                <div><dt>Policy</dt><dd>{decision.policyVersion}</dd></div>
                <div><dt>Evidence</dt><dd>{decision.evidenceId}</dd></div>
                <div><dt>Expires</dt><dd>{new Date(decision.expiresAt).toLocaleString()}</dd></div>
              </dl>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}