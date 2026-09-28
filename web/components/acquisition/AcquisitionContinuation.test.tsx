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

function getRazorpayScript() {
  const script = document.getElementById('razorpay-checkout-script');
  if (!script) throw new Error('Expected the Razorpay checkout script.');
  return script;
}

describe('AcquisitionContinuation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.Razorpay = undefined;
    document.getElementById('razorpay-checkout-script')?.remove();
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

  it('rejects an invalid Razorpay callback and permits the same checkout to be retried', async () => {
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
    act(() => {
      (checkoutOptions?.handler as (payment: object) => void)({
        razorpay_order_id: 'different_order',
        razorpay_payment_id: '',
        razorpay_signature: '',
      });
    });

    expect(
      await screen.findByText('Razorpay returned an invalid payment confirmation. No Hire was started.')
    ).toBeVisible();
    expect(screen.getByRole('button', { name: 'Open Razorpay Checkout' })).toBeEnabled();
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it('keeps an unresolved signed confirmation retryable', async () => {
    let checkoutOptions: Record<string, unknown> | undefined;
    window.Razorpay = jest.fn().mockImplementation((options: Record<string, unknown>) => {
      checkoutOptions = options;
      return { on: jest.fn(), open: jest.fn() };
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
        }),
      })
      .mockResolvedValueOnce({ ok: false, json: async () => ({ title: 'Payment is still reconciling.' }) });

    render(<AcquisitionContinuation {...props} intent="hire" />);
    await waitFor(() => expect(checkoutOptions).toBeDefined());
    await act(async () => {
      (checkoutOptions?.handler as (payment: object) => void)({
        razorpay_order_id: 'order_test123',
        razorpay_payment_id: 'pay_test123',
        razorpay_signature: 'a'.repeat(64),
      });
    });

    expect(await screen.findByText('Payment is still reconciling.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Open Razorpay Checkout' })).toBeEnabled();
    expect(replace).not.toHaveBeenCalled();
  });

  it('shows the Razorpay provider failure without recording Hire success', async () => {
    const on = jest.fn();
    window.Razorpay = jest.fn().mockImplementation(() => ({ on, open: jest.fn() }));
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
    await waitFor(() => expect(on).toHaveBeenCalledWith('payment.failed', expect.any(Function)));
    act(() => on.mock.calls[0][1]({ error: { description: 'Payment was declined.' } }));

    expect(await screen.findByText('Payment was declined.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Open Razorpay Checkout' })).toBeEnabled();
    expect(replace).not.toHaveBeenCalled();
  });

  it('surfaces a retryable trial continuation outage', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ title: 'Customer service is temporarily unavailable.' }),
    });

    render(<AcquisitionContinuation {...props} />);

    expect(await screen.findByText('Customer service is temporarily unavailable.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Open Razorpay Checkout' })).toBeEnabled();
    expect(replace).not.toHaveBeenCalled();
  });

  it('loads the official Razorpay script when Checkout is not already present', async () => {
    const open = jest.fn();
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
    await waitFor(() => expect(document.getElementById('razorpay-checkout-script')).toBeInTheDocument());
    window.Razorpay = jest.fn().mockImplementation(() => ({ on: jest.fn(), open }));
    fireEvent.load(getRazorpayScript());

    await waitFor(() => expect(open).toHaveBeenCalledTimes(1));
    expect(getRazorpayScript()).toHaveAttribute('src', 'https://checkout.razorpay.com/v1/checkout.js');
  });

  it('reports a failure to load the official Razorpay script', async () => {
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
    await waitFor(() => expect(document.getElementById('razorpay-checkout-script')).toBeInTheDocument());
    fireEvent.error(getRazorpayScript());

    expect(await screen.findByText('Secure Razorpay Checkout could not be loaded.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Cancel' })).toBeVisible();
  });
});
