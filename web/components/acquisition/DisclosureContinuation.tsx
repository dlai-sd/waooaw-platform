'use client';

// Implements: work-contracts/WC-107-fundamental-customer-journey-integrity.md R009, R010, R012, R017
// Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { AcquisitionContinuation, type AcquisitionContinuationProps } from './AcquisitionContinuation';

type AcquisitionIntent = 'trial' | 'hire';

export function DisclosureContinuation({
  disclosureRevision,
  initialIntent,
  professionalType,
  professionalVersion,
  termsVersion,
  priceInrPaise,
  trialAvailable,
  trialDurationDays,
}: {
  disclosureRevision: string;
  initialIntent?: AcquisitionIntent;
  professionalType: string;
  professionalVersion: string;
  termsVersion: string;
  priceInrPaise?: number;
  trialAvailable: boolean;
  trialDurationDays?: number;
}) {
  const [accepted, setAccepted] = useState(false);
  const [couponCode, setCouponCode] = useState('');
  const [appliedCoupon, setAppliedCoupon] = useState<string | null>(null);
  const [payableInrPaise, setPayableInrPaise] = useState(priceInrPaise ?? 0);
  const [couponStatus, setCouponStatus] = useState<string | null>(null);
  const [checkingCoupon, setCheckingCoupon] = useState(false);
  const [continuation, setContinuation] = useState<AcquisitionContinuationProps | null>(null);
  const intents: AcquisitionIntent[] = initialIntent ? [initialIntent] : trialAvailable ? ['trial', 'hire'] : ['hire'];

  useEffect(() => {
    setAccepted(false);
    setAppliedCoupon(null);
    setCouponCode('');
    setCouponStatus(null);
    setPayableInrPaise(priceInrPaise ?? 0);
    setContinuation(null);
  }, [disclosureRevision, priceInrPaise, professionalType, professionalVersion, termsVersion]);

  function continueWith(intent: AcquisitionIntent) {
    if (!accepted) return;
    setContinuation({
      professionalType,
      professionalVersion,
      intent,
      disclosureRevision,
      termsVersion,
      idempotencyKey: crypto.randomUUID(),
      ...(intent === 'hire' && appliedCoupon ? { couponCode: appliedCoupon } : {}),
    });
  }

  async function applyCoupon() {
    const normalized = couponCode.trim().toUpperCase();
    if (!normalized) return;
    setCheckingCoupon(true);
    setCouponStatus(null);
    try {
      const response = await fetch('/api/acquisition/hire-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ professionalType, professionalVersion, couponCode: normalized }),
      });
      const result = (await response.json().catch(() => ({}))) as {
        coupon_code?: string;
        payable_inr_paise?: number;
        title?: string;
        detail?: { code?: string };
      };
      if (!response.ok || result.coupon_code !== normalized || typeof result.payable_inr_paise !== 'number') {
        setAppliedCoupon(null);
        setPayableInrPaise(priceInrPaise ?? 0);
        setCouponStatus(
          result.detail?.code === 'COUPON_EXPIRED'
            ? 'That coupon has expired.'
            : result.detail?.code === 'COUPON_USED'
              ? 'That coupon has reached its usage limit.'
              : 'That coupon is not available for this offer.'
        );
        return;
      }
      setAppliedCoupon(normalized);
      setPayableInrPaise(result.payable_inr_paise);
      setCouponStatus(
        `Coupon applied. Amount due now: ${new Intl.NumberFormat('en-IN', {
          style: 'currency',
          currency: 'INR',
        }).format(result.payable_inr_paise / 100)}.`
      );
    } catch {
      setAppliedCoupon(null);
      setPayableInrPaise(priceInrPaise ?? 0);
      setCouponStatus('Coupon validation is unavailable. You can continue without a coupon or try again.');
    } finally {
      setCheckingCoupon(false);
    }
  }

  if (continuation) return <AcquisitionContinuation {...continuation} />;

  const hireAmount = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
  }).format(payableInrPaise / 100);

  return (
    <section className="disclosure-continuation" aria-labelledby="disclosure-decision-title">
      <h2 id="disclosure-decision-title">Ready to continue?</h2>
      <label>
        <input checked={accepted} onChange={(event) => setAccepted(event.target.checked)} type="checkbox" />{' '}
        <span>
          I agree to the <Link href="/terms">Terms</Link> and acknowledge the{' '}
          <Link href="/privacy">Privacy Policy</Link>.
        </span>
      </label>
      <p className="offer-terms-version">Terms version {termsVersion}. Nothing starts until you continue.</p>
      {intents.includes('hire') ? (
        <div className="disclosure-coupon">
          <label htmlFor="disclosure-coupon-code">
            Coupon code <span>(optional)</span>
          </label>
          <div>
            <input
              id="disclosure-coupon-code"
              autoComplete="off"
              placeholder="Enter coupon code"
              onChange={(event) => {
                setCouponCode(event.target.value.toUpperCase());
                setAppliedCoupon(null);
                setPayableInrPaise(priceInrPaise ?? 0);
                setCouponStatus(null);
              }}
              value={couponCode}
            />
            <button disabled={!couponCode.trim() || checkingCoupon} onClick={() => void applyCoupon()} type="button">
              {checkingCoupon ? 'Checking...' : 'Apply'}
            </button>
          </div>
          {couponStatus ? <p aria-live="polite">{couponStatus}</p> : null}
        </div>
      ) : null}
      <div className="command-row">
        {intents.includes('trial') ? (
          <button className="primary-command" disabled={!accepted} onClick={() => continueWith('trial')} type="button">
            {trialDurationDays ? `Start ${trialDurationDays}-day trial` : 'Start trial'}
          </button>
        ) : null}
        {intents.includes('hire') ? (
          <button
            className={initialIntent === 'hire' ? 'primary-command' : 'secondary-command'}
            disabled={!accepted}
            onClick={() => continueWith('hire')}
            type="button"
          >
            {priceInrPaise !== undefined ? `Hire for ${hireAmount}` : 'Hire'}
          </button>
        ) : null}
        <Link className="text-command" href="/marketplace">
          Not now
        </Link>
      </div>
    </section>
  );
}
