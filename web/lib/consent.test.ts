// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Consent Categories And State
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { consentCookieName, createConsentPreference, optionalConsent, parseConsentCookie } from './consent';

describe('versioned consent preference', () => {
  it('round trips only the current granular preference', () => {
    const preference = createConsentPreference(true, false);
    expect(parseConsentCookie(`${consentCookieName}=${encodeURIComponent(JSON.stringify(preference))}`)).toEqual(preference);
  });
  it('rejects stale and malformed preferences', () => {
    expect(parseConsentCookie(`${consentCookieName}=%7Bbad`)).toBeNull();
    expect(parseConsentCookie(`${consentCookieName}=${encodeURIComponent(JSON.stringify({ ...createConsentPreference(true, true), policyVersion: 'old' }))}`)).toBeNull();
  });
  it('lets DNT or GPC override every optional category', () => expect(optionalConsent(createConsentPreference(true, true), true)).toEqual({ analytics: false, advertising: false }));
});