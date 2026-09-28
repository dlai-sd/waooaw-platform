import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DisclosureContinuation } from './DisclosureContinuation';

jest.mock('./AcquisitionContinuation', () => ({
  AcquisitionContinuation: (props: object) => <output data-testid="continuation">{JSON.stringify(props)}</output>,
}));
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
        priceInrPaise={249900}
        trialAvailable
        trialDurationDays={14}
      />
    );

    const continueButton = screen.getByRole('button', { name: 'Start 14-day trial' });
    expect(continueButton).toBeDisabled();
    expect(screen.getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms');
    expect(screen.getByRole('link', { name: 'Privacy Policy' })).toHaveAttribute('href', '/privacy');
    expect(screen.queryByRole('button', { name: 'Continue to hire' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(continueButton);

    expect(JSON.parse(screen.getByTestId('continuation').textContent ?? '{}')).toEqual({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      professionalVersion: '1.0.0',
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
        priceInrPaise={249900}
        trialAvailable
        trialDurationDays={14}
      />
    );

    expect(screen.getByRole('link', { name: 'Not now' })).toHaveAttribute('href', '/marketplace');
    expect(screen.queryByTestId('continuation')).not.toBeInTheDocument();
  });

  it('withdraws consent and requires fresh consent when the offer contract changes', () => {
    const { rerender } = render(
      <DisclosureContinuation
        disclosureRevision="1.0.0"
        initialIntent="hire"
        professionalType="DIGITAL_MARKETING_LOCAL_SERVICE"
        professionalVersion="1.0.0"
        termsVersion="2026-07-18"
        priceInrPaise={249900}
        trialAvailable
        trialDurationDays={14}
      />
    );
    const consent = screen.getByRole('checkbox');
    fireEvent.click(consent);
    expect(screen.getByRole('button', { name: 'Hire for ₹2,499.00' })).toBeEnabled();
    fireEvent.click(consent);
    expect(screen.getByRole('button', { name: 'Hire for ₹2,499.00' })).toBeDisabled();
    expect(screen.queryByTestId('continuation')).not.toBeInTheDocument();

    fireEvent.click(consent);
    rerender(
      <DisclosureContinuation
        disclosureRevision="1.0.1"
        initialIntent="hire"
        professionalType="DIGITAL_MARKETING_LOCAL_SERVICE"
        professionalVersion="1.0.0"
        termsVersion="2026-07-19"
        priceInrPaise={249900}
        trialAvailable
        trialDurationDays={14}
      />
    );
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(screen.getByRole('button', { name: 'Hire for ₹2,499.00' })).toBeDisabled();
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
        priceInrPaise={249900}
        trialAvailable
        trialDurationDays={14}
      />
    );

    fireEvent.change(screen.getByLabelText('Coupon code (optional)'), { target: { value: 'demo100' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
    expect(await screen.findByText('Coupon applied. Amount due now: ₹0.00.')).toBeVisible();
    expect(global.fetch).toHaveBeenCalledWith('/api/acquisition/hire-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
        professionalVersion: '1.0.0',
        couponCode: 'DEMO100',
      }),
    });
    const locationBeforeCommand = window.location.href;
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Hire for ₹0.00' }));

    await waitFor(() => expect(screen.getByTestId('continuation')).toBeVisible());
    expect(window.location.href).toBe(locationBeforeCommand);
    expect(JSON.parse(screen.getByTestId('continuation').textContent ?? '{}')).toEqual(
      expect.objectContaining({ couponCode: 'DEMO100', intent: 'hire' })
    );
  });

  it.each([
    ['COUPON_EXPIRED', 'That coupon has expired.'],
    ['COUPON_USED', 'That coupon has reached its usage limit.'],
    ['COUPON_NOT_APPLICABLE', 'That coupon is not available for this offer.'],
  ])('rejects %s without changing the exact Hire amount', async (code, message) => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: { code } }),
    });
    render(
      <DisclosureContinuation
        disclosureRevision="1.0.0"
        initialIntent="hire"
        professionalType="DIGITAL_MARKETING_LOCAL_SERVICE"
        professionalVersion="1.0.0"
        termsVersion="2026-07-18"
        priceInrPaise={249900}
        trialAvailable
        trialDurationDays={14}
      />
    );

    fireEvent.change(screen.getByLabelText('Coupon code (optional)'), { target: { value: 'invalid' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    expect(await screen.findByText(message)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Hire for ₹2,499.00' })).toBeDisabled();
  });
});
