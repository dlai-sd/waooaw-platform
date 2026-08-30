// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Attribution, Retention, And Failure
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { fireEvent, render, waitFor } from '@testing-library/react';
import { AcquisitionController, recordAcquisitionEvent } from './AcquisitionController';
import { consentCookieName, createConsentPreference } from '@/lib/consent';

jest.mock('next/navigation', () => ({ usePathname: () => '/contact' }));

describe('public acquisition controller', () => {
  beforeEach(() => {
    document.cookie = `${consentCookieName}=; Max-Age=0; Path=/`;
    sessionStorage.clear();
    global.fetch = jest.fn(async () => ({ ok: true } as Response));
  });

  it('creates no optional storage or request before consent', () => {
    render(<AcquisitionController />);
    expect(sessionStorage).toHaveLength(0);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('emits minimized consent, page, and contact events after consent', async () => {
    const preference = createConsentPreference(true, false);
    document.cookie = `${consentCookieName}=${encodeURIComponent(JSON.stringify(preference))}; Path=/`;
    render(<><AcquisitionController /><a href="mailto:customersupport@dlaisd.com" onClick={(event) => event.preventDefault()}>Contact</a></>);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    fireEvent.click(document.querySelector('a') as HTMLAnchorElement);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    const bodies = jest.mocked(fetch).mock.calls.map(([, request]) => JSON.parse(String(request?.body)) as Record<string, unknown>);
    expect(bodies.map((body) => body.event_name)).toEqual(['public_page_viewed', 'contact_invoked']);
    expect(bodies[1]).not.toHaveProperty('email');
    expect(sessionStorage.getItem('waooaw:acquisition:session')).toContain('expiresAt');
  });

  it('keeps destination failures private and non-blocking', async () => {
    jest.mocked(fetch).mockRejectedValue(new Error('destination unavailable'));
    expect(() => recordAcquisitionEvent('consent_updated', { analytics: true, advertising: false })).not.toThrow();
    await Promise.resolve();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('distinguishes registration from a professional hire journey', async () => {
    const preference = createConsentPreference(true, false);
    document.cookie = `${consentCookieName}=${encodeURIComponent(JSON.stringify(preference))}; Path=/`;
    render(<><AcquisitionController /><a href="/register">Register</a><a href="/register?professional=digital-marketing">Hire</a></>);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    fireEvent.click(document.querySelector('a[href="/register"]') as HTMLAnchorElement);
    fireEvent.click(document.querySelector('a[href*="professional="]') as HTMLAnchorElement);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    const bodies = jest.mocked(fetch).mock.calls.map(([, request]) => JSON.parse(String(request?.body)) as Record<string, unknown>);
    expect(bodies.slice(1).map((body) => body.event_name)).toEqual(['registration_started', 'hire_journey_started']);
    expect(bodies[2]).toMatchObject({ entry_route: '/contact', professional_type: 'digital-marketing' });
  });
});