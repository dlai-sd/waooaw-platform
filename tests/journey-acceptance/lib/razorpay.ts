// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 W3 Provider (Razorpay test API)
// Constitutional basis: C-059 (Implementation Traceability), C-023 (Evidence First)
import { createHmac } from "node:crypto";

export type FetchLike = (url: string, init?: { method?: string; headers?: Record<string, string>; body?: string }) => Promise<{
  ok: boolean;
  status: number;
  text(): Promise<string>;
}>;

export class ProviderModeError extends Error {}

/** A live credential stops the run with a configuration finding; the harness never touches a non-sandbox provider (AD-006). */
export function assertRazorpayTestMode(keyId: string, prefix = "rzp_test_"): void {
  if (!keyId.startsWith(prefix)) {
    throw new ProviderModeError(`Razorpay key id does not begin ${prefix}; refusing to call the provider`);
  }
}

/** Razorpay signs a webhook as the hex HMAC-SHA256 of the raw body with the webhook secret. */
export function signWebhook(rawBody: string, secret: string): string {
  return createHmac("sha256", secret).update(rawBody).digest("hex");
}

export interface PaymentSummary {
  paymentId: string;
  status: string;
  amountPaise: number;
  captured: boolean;
}

/** Reads the payments for one order straight from the Razorpay sandbox API (W3). */
export async function readOrderPayments(
  fetchImpl: FetchLike,
  credentials: { keyId: string; keySecret: string },
  orderId: string,
): Promise<PaymentSummary[]> {
  assertRazorpayTestMode(credentials.keyId);
  if (!/^order_[A-Za-z0-9_-]{1,120}$/.test(orderId)) {
    throw new ProviderModeError("order identifier is not a Razorpay order id");
  }
  const authorization = `Basic ${Buffer.from(`${credentials.keyId}:${credentials.keySecret}`).toString("base64")}`;
  const response = await fetchImpl(`https://api.razorpay.com/v1/orders/${orderId}/payments`, {
    headers: { Authorization: authorization },
  });
  if (!response.ok) {
    throw new ProviderModeError(`Razorpay answered HTTP ${response.status}`);
  }
  const body = JSON.parse(await response.text()) as { items?: { id: string; status: string; amount: number; captured?: boolean }[] };
  return (body.items ?? []).map((item) => ({
    paymentId: item.id,
    status: item.status,
    amountPaise: item.amount,
    captured: item.status === "captured" || item.captured === true,
  }));
}

export function capturedTotal(payments: PaymentSummary[]): { count: number; amountPaise: number } {
  const captured = payments.filter((payment) => payment.captured);
  return { count: captured.length, amountPaise: captured.reduce((sum, payment) => sum + payment.amountPaise, 0) };
}
