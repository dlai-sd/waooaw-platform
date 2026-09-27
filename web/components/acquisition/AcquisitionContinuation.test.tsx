import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AcquisitionContinuation, type AcquisitionContinuationProps } from './AcquisitionContinuation';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));
const originalFetch = global.fetch;
const props: AcquisitionContinuationProps = {
  professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
  professionalVersion: '1.0.0',
  intent: 'trial',
  disclosureRevision: '1.0.0',
  termsVersion: '2026-07-18',
  idempotencyKey: '11111111-1111-4111-8111-111111111111',
};

describe('AcquisitionContinuation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('submits the accepted binding and follows only the server resume path', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ resumePath: '/relationships/22222222-2222-4222-8222-222222222222' }),
    });
    render(<AcquisitionContinuation {...props} />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/relationships/22222222-2222-4222-8222-222222222222'));
    expect(jest.mocked(fetch)).toHaveBeenCalledWith(
      '/api/acquisition/continue',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(props),
      })
    );
  });

  it('requires an explicitly applied coupon before creating a zero-price Hire relationship', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          outcome_kind: 'PAYMENT_REQUIRED_AFTER_CONTRACT',
          list_price_inr_paise: 118000,
          discount_inr_paise: 0,
          tax_inr_paise: 18000,
          payable_inr_paise: 118000,
          currency: 'INR',
          cadence: 'MONTHLY',
          provider: 'RAZORPAY',
          payment_method_required: true,
          payments_enabled: false,
          renewal_consequence: 'Standard paid renewal terms apply after the Demo period.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          outcome_kind: 'FULLY_DISCOUNTED',
          list_price_inr_paise: 118000,
          discount_inr_paise: 118000,
          tax_inr_paise: 18000,
          payable_inr_paise: 0,
          currency: 'INR',
          cadence: 'MONTHLY',
          coupon_code: 'DEMO100',
          provider: 'RAZORPAY',
          payment_method_required: false,
          payments_enabled: false,
          renewal_consequence: 'Standard paid renewal terms apply after the Demo period.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ resumePath: '/relationships/22222222-2222-4222-8222-222222222222' }),
      });

    render(<AcquisitionContinuation {...props} intent="hire" />);

    expect(await screen.findByRole('dialog', { name: 'Review your hire' })).toBeVisible();
    expect(screen.getByAltText('WAOOAW')).toBeVisible();
    expect(screen.getByLabelText('Discount coupon')).toHaveValue('');
    expect(screen.getByText('Total due now').nextSibling).toHaveTextContent('₹1,180.00');
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    expect(screen.queryByText('Secured by Razorpay')).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
    expect(jest.mocked(fetch)).toHaveBeenCalledTimes(1);
    expect(jest.mocked(fetch)).toHaveBeenNthCalledWith(
      1,
      '/api/acquisition/hire-preview',
      expect.objectContaining({ method: 'POST' })
    );

    fireEvent.change(screen.getByLabelText('Discount coupon'), { target: { value: 'demo100' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    expect(await screen.findByText('Applied')).toBeVisible();
    expect(screen.getByText('Total due now').nextSibling).toHaveTextContent('₹0.00');
    expect(screen.getByText(/Congratulations! DEMO100 gives you 100% off this hire/)).toHaveTextContent(
      'We wish you great business success with your WAOOAW professional!'
    );
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body))).toEqual({
      professionalType: props.professionalType,
      professionalVersion: props.professionalVersion,
      couponCode: 'DEMO100',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Continue to agent configuration' }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/relationships/22222222-2222-4222-8222-222222222222'));
    expect(jest.mocked(fetch)).toHaveBeenNthCalledWith(
      3,
      '/api/acquisition/continue',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('blocks a non-zero checkout when payments are disabled', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcome_kind: 'PAYMENT_REQUIRED_AFTER_CONTRACT',
        list_price_inr_paise: 118000,
        discount_inr_paise: 0,
        tax_inr_paise: 18000,
        payable_inr_paise: 118000,
        currency: 'INR',
        cadence: 'MONTHLY',
        provider: 'RAZORPAY',
        payment_method_required: true,
        payments_enabled: false,
        renewal_consequence: 'Standard paid renewal terms apply.',
      }),
    });
    render(<AcquisitionContinuation {...props} intent="hire" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Continue to agent configuration' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Great news! Hiring is free of charge in the Demo / UAT environment'
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Thank you for choosing WAOOAW');
    expect(jest.mocked(fetch)).toHaveBeenCalledTimes(1);
    expect(replace).not.toHaveBeenCalled();
  });

  it.each([
    ['COUPON_NOT_FOUND', 'We could not find that coupon. Check the code and try again.'],
    ['COUPON_EXPIRED', 'That coupon has expired. Please try another coupon.'],
    ['COUPON_USED', 'That coupon has reached its usage limit. Please try another coupon.'],
    ['COUPON_AGENT_MISMATCH', 'That coupon is not available for this professional. Please try another coupon.'],
    ['COUPON_TIER_MISMATCH', 'That coupon is not available for this plan. Please try another coupon.'],
    ['DISCOUNT_EXCEEDS_CAP', 'That coupon cannot be applied under the current discount policy.'],
  ])('shows appropriate guidance for %s', async (code, message) => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          outcome_kind: 'PAYMENT_REQUIRED_AFTER_CONTRACT',
          list_price_inr_paise: 118000,
          discount_inr_paise: 0,
          tax_inr_paise: 18000,
          payable_inr_paise: 118000,
          currency: 'INR',
          cadence: 'MONTHLY',
          provider: 'RAZORPAY',
          payment_method_required: true,
          payments_enabled: false,
          renewal_consequence: 'Standard paid renewal terms apply.',
        }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ detail: { code } }),
      });
    render(<AcquisitionContinuation {...props} intent="hire" />);

    fireEvent.change(await screen.findByLabelText('Discount coupon'), { target: { value: 'invalid-code' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.getByText('Total due now').nextSibling).toHaveTextContent('₹1,180.00');
    expect(replace).not.toHaveBeenCalled();
  });

  it('makes an uncertain outcome retryable without changing the idempotency key', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ title: 'Unavailable' }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ resumePath: '/relationships/22222222-2222-4222-8222-222222222222' }),
      });
    render(<AcquisitionContinuation {...props} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Try same request again' }));
    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[0][1]?.body)).idempotencyKey).toBe(props.idempotencyKey);
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body)).idempotencyKey).toBe(props.idempotencyKey);
  });

  it('does not offer a retry for a known unavailable Trial and directs the customer to My Agents', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ title: 'Trial is currently unavailable' }),
    });
    render(<AcquisitionContinuation {...props} />);

    expect(await screen.findByRole('heading', { name: 'Trial is currently unavailable' })).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View My Agents' })).toHaveAttribute('href', '/professionals/mine');
  });

  it('requires registration without implying that a professional was started', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ code: 'REGISTRATION_REQUIRED', title: 'Complete registration first' }),
    });
    render(<AcquisitionContinuation {...props} />);

    expect(await screen.findByRole('heading', { name: 'Complete registration first' })).toBeInTheDocument();
    expect(screen.getByText('The request was not accepted and no professional was started.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Complete registration' })).toHaveAttribute('href', '/register');
    expect(screen.queryByRole('link', { name: 'View My Agents' })).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it('requires sign in after an expired session without implying success', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ title: 'Secure sign in is required.' }),
    });
    render(<AcquisitionContinuation {...props} />);

    expect(await screen.findByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
    expect(screen.queryByRole('link', { name: 'View My Agents' })).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});
