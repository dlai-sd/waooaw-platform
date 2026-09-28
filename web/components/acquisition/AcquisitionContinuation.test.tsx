import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
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
    window.Razorpay = undefined;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('keeps Trial paymentless and follows only the server resume path', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ resumePath: '/relationships/22222222-2222-4222-8222-222222222222' }),
    });
    render(<AcquisitionContinuation {...props} />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/relationships/22222222-2222-4222-8222-222222222222'));
    expect(jest.mocked(fetch)).toHaveBeenCalledWith(
      '/api/acquisition/continue',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(props) })
    );
  });

  it('opens official Razorpay Checkout and submits its signed callback before starting Hire', async () => {
    let checkoutOptions: Record<string, unknown> | undefined;
    const open = jest.fn();
    window.Razorpay = jest.fn().mockImplementation((options: Record<string, unknown>) => {
      checkoutOptions = options;
      return { on: jest.fn(), open };
    });
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          outcome_kind: 'RAZORPAY_CHECKOUT_REQUIRED',
          checkout_intent_id: props.idempotencyKey,
          provider_order_reference: 'order_test123',
          public_checkout_key: 'rzp_test_public',
          amount_inr_paise: 118000,
          currency: 'INR',
          merchant_display_name: 'WAOOAW',
          enabled_method_families: ['card', 'upi'],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ resumePath: '/relationships/22222222-2222-4222-8222-222222222222' }),
      });

    render(<AcquisitionContinuation {...props} intent="hire" />);

    await waitFor(() => expect(open).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(checkoutOptions).toEqual(
      expect.objectContaining({
        key: 'rzp_test_public',
        amount: 118000,
        currency: 'INR',
        image: 'https://raw.githubusercontent.com/dlai-sd/waooaw-platform/main/web/public/waooaw-platform-logo.png',
        order_id: 'order_test123',
      })
    );
    await act(async () => {
      await (checkoutOptions?.handler as (payment: object) => void)({
        razorpay_order_id: 'order_test123',
        razorpay_payment_id: 'pay_test123',
        razorpay_signature: 'a'.repeat(64),
      });
    });

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/relationships/22222222-2222-4222-8222-222222222222'));
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body))).toEqual(
      expect.objectContaining({
        action: 'confirm',
        razorpayOrderId: 'order_test123',
        razorpayPaymentId: 'pay_test123',
        razorpaySignature: 'a'.repeat(64),
      })
    );
  });

  it('bypasses Razorpay for a server-validated fully discounted Hire', async () => {
    const razorpay = jest.fn();
    window.Razorpay = razorpay;
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcome_kind: 'FULLY_DISCOUNTED',
        resumePath: '/relationships/22222222-2222-4222-8222-222222222222',
      }),
    });

    render(<AcquisitionContinuation {...props} couponCode="DEMO100" intent="hire" />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/relationships/22222222-2222-4222-8222-222222222222'));
    expect(razorpay).not.toHaveBeenCalled();
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[0][1]?.body))).toEqual(
      expect.objectContaining({
        action: 'start',
        couponCode: 'DEMO100',
      })
    );
  });

  it('stops loading and offers an exit when Razorpay is not configured', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcome_kind: 'PROVIDER_CONFIGURATION_PENDING',
        customer_safe_next_action: 'Razorpay Checkout is not configured for this environment.',
      }),
    });

    render(<AcquisitionContinuation {...props} intent="hire" />);

    expect(await screen.findByText('Razorpay Checkout is not configured for this environment.')).toBeVisible();
    expect(screen.queryByText('Opening secure Razorpay Checkout...')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Open Razorpay Checkout' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Cancel' })).toHaveAttribute('href', '/marketplace');
  });

  it('replays the same intent after Razorpay is dismissed', async () => {
    let checkoutOptions: Record<string, unknown> | undefined;
    window.Razorpay = jest.fn().mockImplementation((options: Record<string, unknown>) => {
      checkoutOptions = options;
      return { on: jest.fn(), open: jest.fn() };
    });
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcome_kind: 'RAZORPAY_CHECKOUT_REQUIRED',
        checkout_intent_id: props.idempotencyKey,
        provider_order_reference: 'order_test123',
        public_checkout_key: 'rzp_test_public',
        amount_inr_paise: 118000,
        currency: 'INR',
        merchant_display_name: 'WAOOAW',
      }),
    });

    render(<AcquisitionContinuation {...props} intent="hire" />);
    await waitFor(() => expect(checkoutOptions).toBeDefined());
    act(() => (checkoutOptions?.modal as { ondismiss: () => void }).ondismiss());
    fireEvent.click(await screen.findByRole('button', { name: 'Open Razorpay Checkout' }));

    await waitFor(() => expect(jest.mocked(fetch)).toHaveBeenCalledTimes(2));
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[0][1]?.body)).idempotencyKey).toBe(props.idempotencyKey);
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body)).idempotencyKey).toBe(props.idempotencyKey);
  });
});
