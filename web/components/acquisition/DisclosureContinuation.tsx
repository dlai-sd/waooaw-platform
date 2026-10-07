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
  const [selectedIntent, setSelectedIntent] = useState<AcquisitionIntent | undefined>(initialIntent);
  const offerIdentity = `${professionalType}\u001f${professionalVersion}\u001f${disclosureRevision}\u001f${termsVersion}`;

  useEffect(() => {
    if (!offerIdentity) return;
    setSelectedIntent(initialIntent);
    setAccepted(false);
    setAppliedCoupon(null);
    setCouponCode('');
    setCouponStatus(null);
    setPayableInrPaise(priceInrPaise ?? 0);
    setContinuation(null);
  }, [initialIntent, offerIdentity, priceInrPaise]);

  function continueWith(intent: AcquisitionIntent) {
    if (!accepted) return;
    setContinuation({
      professionalType,
      professionalVersion,
      intent,
      disclosureRevision,
      termsVersion,
      idempotencyKey: crypto.randomUUID(),
      contractAcceptance: 'ACCEPT_EMPLOYMENT_CONTRACT',
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
  if (!selectedIntent) {
    return (
      <section className="disclosure-continuation" aria-labelledby="acquisition-mode-title">
        <h2 id="acquisition-mode-title">Choose Trial or Hire</h2>
        <p>Select one mode to review its exact Employment Contract and checkout terms.</p>
        <div className="command-row">
          {trialAvailable ? (
            <button className="primary-command" onClick={() => setSelectedIntent('trial')} type="button">
              Review free {trialDurationDays ?? 14}-day Trial
            </button>
          ) : null}
          <button
            className={trialAvailable ? 'secondary-command' : 'primary-command'}
            onClick={() => setSelectedIntent('hire')}
            type="button"
          >
            Review Hire
          </button>
          <Link className="text-command" href="/marketplace">
            Not now
          </Link>
        </div>
      </section>
    );
  }

  const hireAmount = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
  }).format(payableInrPaise / 100);
  const trialMode = selectedIntent === 'trial';
  const zeroPayableHire = selectedIntent === 'hire' && appliedCoupon !== null && payableInrPaise === 0;
  const contractPath =
    `/employment-contract?professionalType=${encodeURIComponent(professionalType)}` +
    `&version=${encodeURIComponent(professionalVersion)}` +
    `&disclosureRevision=${encodeURIComponent(disclosureRevision)}` +
    `&termsVersion=${encodeURIComponent(termsVersion)}` +
    `&mode=${trialMode ? 'trial' : 'hire'}`;

  return (
    <section className="disclosure-continuation" aria-labelledby="disclosure-decision-title">
      <h2 id="disclosure-decision-title">{trialMode ? 'Free Trial checkout' : 'Hire checkout'}</h2>
      {trialMode ? (
        <div className="identity-status">
          <strong>Free Trial - {trialDurationDays ?? 14} days</strong>
          <span>Amount due now: ₹0.00. The Trial does not convert to paid Hire automatically.</span>
        </div>
      ) : null}
      <label>
        <input checked={accepted} onChange={(event) => setAccepted(event.target.checked)} type="checkbox" />{' '}
        <span>
          I have opened and accept the{' '}
          <Link href={contractPath} target="_blank">
            Employment Contract
          </Link>{' '}
          for this {trialMode ? 'Trial' : 'Hire'} and acknowledge the <Link href="/privacy">Privacy Policy</Link>.
        </span>
      </label>
      <p className="offer-terms-version">Contract version {termsVersion}. Nothing starts until you confirm.</p>
      {trialMode ? (
        <div className="disclosure-coupon">
          <label htmlFor="trial-coupon-code">Coupon code</label>
          <input id="trial-coupon-code" disabled readOnly value="Not applicable during Trial" />
        </div>
      ) : (
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
      )}
      <fieldset className="checkout-method-preview">
        <legend>Razorpay payment options</legend>
        <p>
          {trialMode
            ? 'Payment is not required during the free Trial.'
            : zeroPayableHire
              ? 'No payment method is required because the payable amount is INR 0.'
              : 'Choose your payment method in secure Razorpay Checkout after confirmation.'}
        </p>
        <div className="command-row" aria-label="Razorpay payment methods">
          {['Credit or debit card', 'UPI', 'Netbanking', 'Wallet'].map((method) => (
            <button disabled={trialMode || zeroPayableHire} key={method} type="button">
              {method}
            </button>
          ))}
        </div>
      </fieldset>
      <div className="command-row">
        {selectedIntent === 'trial' ? (
          <button className="primary-command" disabled={!accepted} onClick={() => continueWith('trial')} type="button">
            {trialDurationDays ? `Confirm free ${trialDurationDays}-day trial` : 'Confirm free trial'}
          </button>
        ) : null}
        {selectedIntent === 'hire' ? (
          <button className="primary-command" disabled={!accepted} onClick={() => continueWith('hire')} type="button">
            {zeroPayableHire
              ? 'Confirm Hire - no payment required'
              : priceInrPaise !== undefined
                ? `Continue to Razorpay - ${hireAmount}`
                : 'Continue to Hire'}
          </button>
        ) : null}
        <Link className="text-command" href="/marketplace">
          Not now
        </Link>
      </div>
    </section>
  );
}
