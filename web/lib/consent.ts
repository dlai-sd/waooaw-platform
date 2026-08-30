// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Consent Categories And State
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { marketingConfig } from '@/config/marketing';

export const consentCookieName = 'waooaw_consent';

export type ConsentPreference = {
  policyVersion: string;
  necessary: true;
  analytics: boolean;
  advertising: boolean;
  updatedAt: string;
};

export function createConsentPreference(analytics: boolean, advertising: boolean): ConsentPreference {
  return { policyVersion: marketingConfig.policyVersion, necessary: true, analytics, advertising, updatedAt: new Date().toISOString() };
}

export function parseConsentCookie(cookieHeader: string | null): ConsentPreference | null {
  const encoded = cookieHeader?.split(';').map((part) => part.trim()).find((part) => part.startsWith(`${consentCookieName}=`))?.slice(consentCookieName.length + 1);
  if (!encoded) return null;
  try {
    const value = JSON.parse(decodeURIComponent(encoded)) as Partial<ConsentPreference>;
    if (value.policyVersion !== marketingConfig.policyVersion || value.necessary !== true || typeof value.analytics !== 'boolean' || typeof value.advertising !== 'boolean' || typeof value.updatedAt !== 'string') return null;
    return value as ConsentPreference;
  } catch { return null; }
}

export function optionalConsent(preference: ConsentPreference | null, privacySignal = false) {
  return {
    analytics: !privacySignal && preference?.analytics === true,
    advertising: !privacySignal && preference?.advertising === true,
  };
}