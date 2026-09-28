import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ContractJourney, type ContractJourneyProjection } from './ContractJourney';

const journey: ContractJourneyProjection = {
  contractId: '11111111-1111-4111-8111-111111111111',
  version: 1,
  contractHash: 'a'.repeat(64),
  relationshipState: 'CONFIGURING',
  acceptanceState: 'ACCEPTED',
  paymentState: 'NOT_STARTED',
  activationState: 'NOT_STARTED',
  document: {
    professionalDisplayName: 'Digital Marketing Professional',
    rights: ['Inspect evidence'],
    obligations: ['Provide accurate context'],
    limitations: ['Cannot publish without authority'],
    authorityTerms: ['No publishing'],
    stopTerms: ['Emergency Stop remains available'],
    priceTax: {
      currency: 'INR',
      grossAmountInrPaise: 118000,
      gstAmountInrPaise: 18000,
      cadence: 'MONTHLY',
      subscriptionTerms: 'Monthly subscription',
      adSpendTreatment: 'Ad spend is separate',
      cancellationAndRefundTerms: 'Cancel before renewal',
    },
  },
};

const originalFetch = global.fetch;

function getRazorpayScript() {
  const script = document.getElementById('razorpay-checkout-script');
  if (!script) throw new Error('Expected the Razorpay checkout script.');
  return script;
}

describe('ContractJourney Razorpay Standard Checkout', () => {
  afterEach(() => {
    global.fetch = originalFetch;
    Reflect.deleteProperty(window, 'Razorpay');
    document.getElementById('razorpay-checkout-script')?.remove();
  });

  it('opens official Checkout with the server order and reconciles a matching signed callback', async () => {
    const open = jest.fn();
    const on = jest.fn();
    const Razorpay = jest.fn((_options: Record<string, unknown>) => ({ on, open }));
    Object.defineProperty(window, 'Razorpay', { configurable: true, value: Razorpay });
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          outcomeKind: 'RAZORPAY_CHECKOUT_REQUIRED',
          checkoutIntentId: '22222222-2222-4222-8222-222222222222',
          providerOrderReference: 'order_test_123',
          publicCheckoutKey: 'rzp_test_public',
          amountInrPaise: 118000,
          currency: 'INR',
          merchantDisplayName: 'WAOOAW',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ outcomeKind: 'CAPTURED' }),
      });

    render(<ContractJourney journey={journey} relationshipId="33333333-3333-4333-8333-333333333333" />);
    fireEvent.click(screen.getByRole('button', { name: 'Confirm contract funding' }));

    await waitFor(() => expect(Razorpay).toHaveBeenCalledTimes(1));
    const options = Razorpay.mock.calls[0][0] as Record<string, unknown> & {
      handler: (response: Record<string, string>) => void;
    };
    expect(options).toEqual(
      expect.objectContaining({
        key: 'rzp_test_public',
        amount: 118000,
        currency: 'INR',
        name: 'WAOOAW',
        image: 'https://raw.githubusercontent.com/dlai-sd/waooaw-platform/main/web/public/waooaw-platform-logo.png',
        order_id: 'order_test_123',
      })
    );
    expect(on).toHaveBeenCalledWith('payment.failed', expect.any(Function));
    expect(open).toHaveBeenCalledTimes(1);

    await act(async () => {
      options.handler({
        razorpay_order_id: 'order_test_123',
        razorpay_payment_id: 'pay_test_123',
        razorpay_signature: 'b'.repeat(64),
      });
    });

    await waitFor(() => expect(jest.mocked(fetch)).toHaveBeenCalledTimes(2));
    expect(jest.mocked(fetch)).toHaveBeenNthCalledWith(
      2,
      '/api/relationships/33333333-3333-4333-8333-333333333333/contract-journey',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          action: 'confirm',
          checkoutIntentId: '22222222-2222-4222-8222-222222222222',
          razorpayOrderId: 'order_test_123',
          razorpayPaymentId: 'pay_test_123',
          razorpaySignature: 'b'.repeat(64),
        }),
      })
    );
  });

  it('accepts the exact contract before exposing funding', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    render(
      <ContractJourney
        journey={{ ...journey, acceptanceState: 'PENDING' }}
        relationshipId="33333333-3333-4333-8333-333333333333"
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Accept exact monthly contract' }));

    expect(await screen.findByText(/Exact monthly contract accepted and evidenced/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Confirm contract funding' })).toBeEnabled();
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[0][1]?.body))).toEqual(
      expect.objectContaining({ action: 'accept', version: 1, contractHash: journey.contractHash })
    );
  });

  it('activates a fully discounted contract with its commercial evidence', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          outcomeKind: 'FULLY_DISCOUNTED',
          couponCode: 'DEMO100',
          listPriceInrPaise: 118000,
          discountInrPaise: 118000,
          commercialOutcomeReference: 'discount-outcome',
          commercialEvidenceId: 'discount-evidence',
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<ContractJourney journey={journey} relationshipId="33333333-3333-4333-8333-333333333333" />);

    fireEvent.click(screen.getByRole('button', { name: 'Confirm contract funding' }));
    expect(
      await screen.findByText('100% Demo discount applied. Amount paid: INR 0. No payment method charged.')
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Complete fully discounted activation' }));

    expect(await screen.findByText('Employment relationship activated. Amount paid: INR 0.')).toBeVisible();
    expect(JSON.parse(String(jest.mocked(fetch).mock.calls[1][1]?.body))).toEqual(
      expect.objectContaining({
        action: 'activate',
        commercialOutcomeKind: 'ZERO_PRICE_SATISFIED',
        commercialOutcomeReference: 'discount-outcome',
        commercialEvidenceId: 'discount-evidence',
      })
    );
  });

  it('does not record success for invalid, failed, or dismissed Razorpay responses', async () => {
    const on = jest.fn();
    const Razorpay = jest.fn((_options: Record<string, unknown>) => ({ on, open: jest.fn() }));
    Object.defineProperty(window, 'Razorpay', { configurable: true, value: Razorpay });
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcomeKind: 'RAZORPAY_CHECKOUT_REQUIRED',
        checkoutIntentId: '22222222-2222-4222-8222-222222222222',
        providerOrderReference: 'order_test_123',
        publicCheckoutKey: 'rzp_test_public',
        amountInrPaise: 118000,
        currency: 'INR',
        merchantDisplayName: 'WAOOAW',
      }),
    });

    render(<ContractJourney journey={journey} relationshipId="33333333-3333-4333-8333-333333333333" />);
    fireEvent.click(screen.getByRole('button', { name: 'Confirm contract funding' }));
    await waitFor(() => expect(Razorpay).toHaveBeenCalledTimes(1));
    const options = Razorpay.mock.calls[0][0] as Record<string, unknown> & {
      handler: (response: Record<string, string>) => void;
      modal: { ondismiss: () => void };
    };

    act(() => options.handler({ razorpay_order_id: 'wrong', razorpay_payment_id: '', razorpay_signature: '' }));
    expect(await screen.findByText(/invalid payment confirmation/)).toBeVisible();
    act(() => on.mock.calls[0][1]({ error: { description: 'Payment declined.' } }));
    expect(await screen.findByText('Payment declined.')).toBeVisible();
    act(() => options.modal.ondismiss());
    expect(await screen.findByText(/Checkout was closed/)).toBeVisible();
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it('keeps a rejected funding command unresolved', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ title: 'Funding is temporarily unavailable.' }),
    });
    render(<ContractJourney journey={journey} relationshipId="33333333-3333-4333-8333-333333333333" />);

    fireEvent.click(screen.getByRole('button', { name: 'Confirm contract funding' }));

    expect(await screen.findByText('Funding is temporarily unavailable.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Confirm contract funding' })).toBeEnabled();
  });

  it('records no state-changing request when the customer defers or cancels', () => {
    global.fetch = jest.fn();
    render(<ContractJourney journey={journey} relationshipId="33333333-3333-4333-8333-333333333333" />);

    fireEvent.click(screen.getByRole('button', { name: 'Not now' }));
    expect(screen.getByText('Not now selected. No contract or payment state changed.')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByText('Cancelled. No contract or payment state changed.')).toBeVisible();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('loads Razorpay Checkout on demand before opening the provider window', async () => {
    const open = jest.fn();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcomeKind: 'RAZORPAY_CHECKOUT_REQUIRED',
        checkoutIntentId: '22222222-2222-4222-8222-222222222222',
        providerOrderReference: 'order_test_123',
        publicCheckoutKey: 'rzp_test_public',
        amountInrPaise: 118000,
        currency: 'INR',
        merchantDisplayName: 'WAOOAW',
      }),
    });
    render(<ContractJourney journey={journey} relationshipId="33333333-3333-4333-8333-333333333333" />);

    fireEvent.click(screen.getByRole('button', { name: 'Confirm contract funding' }));
    await waitFor(() => expect(document.getElementById('razorpay-checkout-script')).toBeInTheDocument());
    Object.defineProperty(window, 'Razorpay', {
      configurable: true,
      value: jest.fn().mockImplementation(() => ({ on: jest.fn(), open })),
    });
    fireEvent.load(getRazorpayScript());

    await waitFor(() => expect(open).toHaveBeenCalledTimes(1));
  });

  it('reports failure when the Razorpay script cannot load', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        outcomeKind: 'RAZORPAY_CHECKOUT_REQUIRED',
        checkoutIntentId: '22222222-2222-4222-8222-222222222222',
        providerOrderReference: 'order_test_123',
        publicCheckoutKey: 'rzp_test_public',
        amountInrPaise: 118000,
        currency: 'INR',
        merchantDisplayName: 'WAOOAW',
      }),
    });
    render(<ContractJourney journey={journey} relationshipId="33333333-3333-4333-8333-333333333333" />);

    fireEvent.click(screen.getByRole('button', { name: 'Confirm contract funding' }));
    await waitFor(() => expect(document.getElementById('razorpay-checkout-script')).toBeInTheDocument());
    fireEvent.error(getRazorpayScript());

    expect(await screen.findByText('Secure Razorpay Checkout could not be loaded.')).toBeVisible();
  });
});
