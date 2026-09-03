'use client';

// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §10.5 (WC-05)
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { cookiePreferencesReopenEvent } from './ConsentController';

export function CookiePreferencesTrigger() {
  return <button className="footer-cookie-trigger" onClick={() => window.dispatchEvent(new Event(cookiePreferencesReopenEvent))} type="button">Cookie preferences</button>;
}
