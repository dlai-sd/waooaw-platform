// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-AUTH-01, §UX-AUTH-03, §UX-AUTH-06, §UX-PRIV-01
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RegistrationFlow } from './RegistrationFlow';
import { getIdentityMessages } from '@/lib/identity-messages';

const registrationId = '8f6f7550-98c7-4a8f-bd63-36f07ee15c9d';
const originalFetch = global.fetch;
const baseRegistration = {
  registrationId, state: 'PROFILE_COMPLETION_REQUIRED', nextAction: 'COMPLETE_PROFILE', authenticationPath: 'GOOGLE',
  emailVerified: true, mobileVerified: false, profile: {}, expiresAt: new Date(), updatedAt: new Date(),
};

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body } as Response);
}

describe('F2 registration flow', () => {
  beforeEach(() => {
    sessionStorage.clear();
    Object.defineProperty(crypto, 'randomUUID', { configurable: true, value: jest.fn(() => '11111111-1111-4111-8111-111111111111') });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('restores and updates only non-secret profile draft fields', async () => {
    sessionStorage.setItem('waooaw:identity:registration-draft', JSON.stringify({ displayName: 'Asha', businessName: 'Field Co', businessDomain: 'Agriculture' }));
    global.fetch = jest.fn(() => jsonResponse(baseRegistration));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    expect(await screen.findByLabelText('Your name')).toHaveValue('Asha');
    fireEvent.change(screen.getByLabelText('Business name'), { target: { value: 'Field Works' } });
    expect(sessionStorage.getItem('waooaw:identity:registration-draft')).toContain('Field Works');
    expect(sessionStorage.getItem('waooaw:identity:registration-draft')).not.toMatch(/email|mobile|code/i);
  });

  it('never persists a one-time code and clears the challenge after confirmation', async () => {
    const verificationRequired = { ...baseRegistration, state: 'EMAIL_VERIFICATION_REQUIRED', nextAction: 'VERIFY_EMAIL', emailVerified: false };
    const challenge = { challengeId: '22222222-2222-4222-8222-222222222222', purpose: 'EMAIL', state: 'PENDING', maskedDestination: 'a***@example.com', expiresAt: new Date(), resendAfter: new Date() };
    global.fetch = jest.fn()
      .mockImplementationOnce(() => jsonResponse(verificationRequired))
      .mockImplementationOnce(() => jsonResponse(challenge))
      .mockImplementationOnce(() => jsonResponse(baseRegistration));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    fireEvent.change(await screen.findByLabelText('Email address'), { target: { value: 'asha@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /Send verification code/ }));
    fireEvent.change(await screen.findByLabelText('Six-digit code'), { target: { value: '123456' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify code/ }));
    await screen.findByLabelText('Your name');

    expect(JSON.stringify(sessionStorage)).not.toContain('123456');
    expect(screen.queryByText('a***@example.com')).not.toBeInTheDocument();
  });

  it('reuses the idempotency key when retrying an uncertain start outcome', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() => Promise.reject(new Error('network unavailable')))
      .mockImplementationOnce(() => jsonResponse(baseRegistration));
    render(<RegistrationFlow locale="en" messages={getIdentityMessages('en')} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }));
    await screen.findByLabelText('Your name');
    const first = JSON.parse(String(jest.mocked(fetch).mock.calls[0][1]?.body));
    const second = JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body));
    expect(second.idempotencyKey).toBe(first.idempotencyKey);
  });
});