// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-AUTH-05, §UX-PRIV-01
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { fireEvent, render, screen } from '@testing-library/react';
import { MobileVerificationFlow } from './MobileVerificationFlow';
import { getIdentityMessages } from '@/lib/identity-messages';

const originalFetch = global.fetch;

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body } as Response);
}

describe('progressive mobile verification', () => {
  beforeEach(() => {
    sessionStorage.clear();
    Object.defineProperty(crypto, 'randomUUID', { configurable: true, value: jest.fn(() => '11111111-1111-4111-8111-111111111111') });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('keeps mobile proof and OTP out of storage and reports unresolved failure honestly', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() => jsonResponse({ challengeId: '22222222-2222-4222-8222-222222222222', purpose: 'MOBILE', state: 'PENDING', maskedDestination: '+91******3210', expiresAt: new Date(), resendAfter: new Date() }))
      .mockImplementationOnce(() => jsonResponse({ code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Verification provider is unavailable.' }, 503));
    render(<MobileVerificationFlow messages={getIdentityMessages('en')} returnTo="/home" />);

    fireEvent.change(screen.getByLabelText('Mobile number'), { target: { value: '+919876543210' } });
    fireEvent.click(screen.getByRole('button', { name: /Send verification code/ }));
    fireEvent.change(await screen.findByLabelText('Six-digit code'), { target: { value: '654321' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify code/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Verification provider is unavailable.');
    expect(JSON.stringify(sessionStorage)).not.toMatch(/9876543210|654321/);
    const confirmation = JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body));
    expect(confirmation).toMatchObject({ action: 'mobile-confirm', code: '654321' });
  });
});