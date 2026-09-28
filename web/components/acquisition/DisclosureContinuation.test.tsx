import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DisclosureContinuation } from './DisclosureContinuation';

const push = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));
const originalFetch = global.fetch;

describe('DisclosureContinuation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(crypto, 'randomUUID', {
      configurable: true,
      value: jest.fn(() => '11111111-1111-4111-8111-111111111111'),
    });
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('requires explicit acceptance and preserves the exact offer binding', () => {
    render(
      <DisclosureContinuation
        disclosureRevision="1.0.0"
        initialIntent="trial"
        professionalType="DIGITAL_MARKETING_LOCAL_SERVICE"
        professionalVersion="1.0.0"
        termsVersion="2026-07-18"
        trialAvailable
      />
    );

    const continueButton = screen.getByRole('button', { name: 'Continue to trial' });
    expect(continueButton).toBeDisabled();
    expect(screen.getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms');
    expect(screen.getByRole('link', { name: 'Privacy Policy' })).toHaveAttribute('href', '/privacy');
    expect(screen.queryByRole('button', { name: 'Continue to hire' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(continueButton);

    const continuationUrl = new URL(push.mock.calls[0][0], 'https://waooaw.test');
    expect(continuationUrl.pathname).toBe('/marketplace');
    expect(Object.fromEntries(continuationUrl.searchParams)).toEqual({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      version: '1.0.0',
      intent: 'trial',
      disclosureRevision: '1.0.0',
      termsVersion: '2026-07-18',
      idempotencyKey: '11111111-1111-4111-8111-111111111111',
    });
  });

  it('offers a no-state-change path back to Marketplace', () => {
    render(
      <DisclosureContinuation
        disclosureRevision="1.0.0"
        professionalType="DIGITAL_MARKETING_LOCAL_SERVICE"
        professionalVersion="1.0.0"
        termsVersion="2026-07-18"
        trialAvailable
      />
    );

    expect(screen.getByRole('link', { name: 'Not now' })).toHaveAttribute('href', '/marketplace');
    expect(push).not.toHaveBeenCalled();
  });

  it('carries a coupon into Hire only after server validation', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ coupon_code: 'DEMO100', payable_inr_paise: 0 }),
    });
    render(
      <DisclosureContinuation
        disclosureRevision="1.0.0"
        initialIntent="hire"
        professionalType="DIGITAL_MARKETING_LOCAL_SERVICE"
        professionalVersion="1.0.0"
        termsVersion="2026-07-18"
        trialAvailable
      />
    );

    fireEvent.change(screen.getByLabelText('Coupon code (optional)'), { target: { value: 'demo100' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
    expect(await screen.findByText('Coupon applied. Amount due now: ₹0.00.')).toBeVisible();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Continue to hire' }));

    await waitFor(() => expect(push).toHaveBeenCalledTimes(1));
    const continuationUrl = new URL(push.mock.calls[0][0], 'https://waooaw.test');
    expect(continuationUrl.searchParams.get('couponCode')).toBe('DEMO100');
  });
});
