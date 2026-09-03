'use client';
// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Consent Categories And State
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { useEffect, useState } from 'react';
import { recordAcquisitionEvent } from './AcquisitionController';
import { consentCookieName, createConsentPreference, optionalConsent, parseConsentCookie } from '@/lib/consent';

const optionalCookieNames = ['_ga', '_gid', '_fbp', '_fbc'];
export const cookiePreferencesReopenEvent = 'waooaw:cookie-preferences:open';

export function ConsentController() {
  const [saved, setSaved] = useState(false);
  const [reopened, setReopened] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [advertising, setAdvertising] = useState(false);
  const [privacySignal, setPrivacySignal] = useState(false);
  useEffect(() => {
    const signal = navigator.doNotTrack === '1' || (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl === true;
    const stored = parseConsentCookie(document.cookie);
    const allowed = optionalConsent(stored, signal);
    setPrivacySignal(signal);
    setAnalytics(allowed.analytics);
    setAdvertising(allowed.advertising);
    setSaved(stored !== null || signal);
  }, []);
  useEffect(() => {
    function reopen() { setReopened(true); setSaved(false); }
    window.addEventListener(cookiePreferencesReopenEvent, reopen);
    return () => window.removeEventListener(cookiePreferencesReopenEvent, reopen);
  }, []);
  function persist(nextAnalytics: boolean, nextAdvertising: boolean) {
    const next = createConsentPreference(privacySignal ? false : nextAnalytics, privacySignal ? false : nextAdvertising);
    document.cookie = `${consentCookieName}=${encodeURIComponent(JSON.stringify(next))}; Path=/; Max-Age=31536000; SameSite=Lax${location.protocol === 'https:' ? '; Secure' : ''}`;
    setAnalytics(next.analytics);
    setAdvertising(next.advertising);
    if (!next.analytics || !next.advertising) optionalCookieNames.forEach((name) => { document.cookie = `${name}=; Path=/; Max-Age=0; SameSite=Lax`; });
    setReopened(false);
    setSaved(true);
    const consent = optionalConsent(next, privacySignal);
    recordAcquisitionEvent('consent_updated', consent, { analytics: consent.analytics, advertising: consent.advertising });
    if (consent.analytics || consent.advertising) recordAcquisitionEvent('public_page_viewed', consent);
  }
  if (saved) return null;
  return <aside className="consent-banner" aria-label="Cookie preferences"><div><strong>{reopened ? 'Review cookie preferences' : 'Your privacy choices'}</strong><p>{reopened ? 'Update your optional categories. Necessary preferences remain on.' : 'Necessary preferences are always on. Optional categories remain off unless selected.'}{privacySignal ? ' Your browser privacy signal keeps optional categories off.' : ''}</p><label><input checked={analytics} disabled={privacySignal} onChange={(event) => setAnalytics(event.target.checked)} type="checkbox" /> Analytics</label><label><input checked={advertising} disabled={privacySignal} onChange={(event) => setAdvertising(event.target.checked)} type="checkbox" /> Advertising</label></div><div><button type="button" onClick={() => persist(false, false)}>Reject optional</button><button type="button" onClick={() => persist(analytics, advertising)}>Save preferences</button><button className="primary-link" type="button" disabled={privacySignal} onClick={() => persist(true, true)}>Accept optional</button></div></aside>;
}