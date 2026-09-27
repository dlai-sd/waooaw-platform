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

describe('ContractJourney Razorpay Standard Checkout', () => {
  afterEach(() => {
    global.fetch = originalFetch;
    Reflect.deleteProperty(window, 'Razorpay');
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
    expect(options).toEqual(expect.objectContaining({
      key: 'rzp_test_public',
      amount: 118000,
      currency: 'INR',
      name: 'WAOOAW',
      image: 'https://raw.githubusercontent.com/dlai-sd/waooaw-platform/main/web/public/waooaw-platform-logo.png',
      order_id: 'order_test_123',
    }));
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
});
