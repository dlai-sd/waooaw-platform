'use client';

// Implements: WC-096 §4.3 Marketplace And Disclosure
// Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

type AcquisitionIntent = 'trial' | 'hire';

export function DisclosureContinuation({ disclosureRevision, initialIntent, professionalType, professionalVersion, termsVersion, trialAvailable }: {
  disclosureRevision: string;
  initialIntent?: AcquisitionIntent;
  professionalType: string;
  professionalVersion: string;
  termsVersion: string;
  trialAvailable: boolean;
}) {
  const router = useRouter();
  const [accepted, setAccepted] = useState(false);
  const intents: AcquisitionIntent[] = initialIntent ? [initialIntent] : trialAvailable ? ['trial', 'hire'] : ['hire'];

  function continueWith(intent: AcquisitionIntent) {
    if (!accepted) return;
    const continuation = new URLSearchParams({
      professionalType,
      version: professionalVersion,
      intent,
      disclosureRevision,
      termsVersion,
      idempotencyKey: crypto.randomUUID(),
    });
    router.push(`/register?returnTo=${encodeURIComponent(`/marketplace?${continuation}`)}`);
  }

  return <section className="disclosure-continuation" aria-labelledby="disclosure-decision-title">
    <h2 id="disclosure-decision-title">Choose how to continue</h2>
    <label><input checked={accepted} onChange={(event) => setAccepted(event.target.checked)} type="checkbox" /> I have reviewed this disclosure and agree to continue under the applicable terms.</label>
    <p>Read the <Link href="/terms">Terms and Conditions</Link> (version {termsVersion}).</p>
    <div className="command-row">
      {intents.includes('trial') ? <button className="primary-command" disabled={!accepted} onClick={() => continueWith('trial')} type="button">Continue to trial</button> : null}
      {intents.includes('hire') ? <button className={initialIntent === 'hire' ? 'primary-command' : 'secondary-command'} disabled={!accepted} onClick={() => continueWith('hire')} type="button">Continue to hire</button> : null}
      <Link className="text-command" href="/marketplace">Not now</Link>
    </div>
  </section>;
}