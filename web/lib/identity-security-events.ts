// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S12
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R007
// Constitutional basis: C-002, C-005, C-059, C-063

import { createHmac } from 'node:crypto';

export type WebIdentityEventType =
  | 'AUTHENTICATION_START'
  | 'PROVIDER_HANDOFF'
  | 'CALLBACK_SUCCESS'
  | 'CALLBACK_FAILURE'
  | 'REFRESH_SUCCESS'
  | 'REFRESH_FAILURE'
  | 'LOGOUT_REQUEST'
  | 'LOGOUT_COMPLETION'
  | 'LOGOUT_FAILURE'
  | 'ACCOUNT_SWITCH'
  | 'SESSION_EXPIRY';

export type WebIdentityProviderClass = 'GOOGLE' | 'FACEBOOK' | 'APPLE' | 'EMAIL' | 'INTERNAL' | 'UNKNOWN';

export interface WebIdentitySecurityEvent {
  correlationId: string;
  sourceEventId?: string;
  eventType: WebIdentityEventType;
  providerClass: WebIdentityProviderClass;
  outcome: 'ATTEMPTED' | 'SUCCEEDED' | 'DENIED' | 'FAILED' | 'CANCELLED';
  reasonCode: string;
  assuranceClass?: 'ANONYMOUS' | 'AAL1' | 'AAL2' | 'AAL3' | 'UNKNOWN';
  occurredAt?: string;
}

export async function persistWebIdentitySecurityEvent(event: WebIdentitySecurityEvent): Promise<boolean> {
  const signingKey = process.env.IDENTITY_EVENT_SIGNING_KEY;
  if (!signingKey || signingKey.length < 32) throw new Error('Identity event signing is unavailable.');
  const body = JSON.stringify({
    ...event,
    sourceEventId: event.sourceEventId ?? `web:${crypto.randomUUID().replaceAll('-', '')}`,
    assuranceClass: event.assuranceClass ?? 'UNKNOWN',
    occurredAt: event.occurredAt ?? new Date().toISOString(),
  });
  const signature = createHmac('sha256', signingKey).update(body).digest('hex');
  const response = await fetch(
    `${process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001'}/internal/identity/security-events`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'X-WAOOAW-Identity-Event-Signature': `sha256=${signature}`,
      },
      body,
      cache: 'no-store',
      signal: AbortSignal.timeout(5_000),
    }
  );
  if (!response.ok) throw new Error(`Identity event persistence failed with status ${response.status}.`);
  return response.status === 201;
}

export async function recordWebIdentitySecurityEvent(event: WebIdentitySecurityEvent): Promise<void> {
  try {
    await persistWebIdentitySecurityEvent(event);
  } catch (error) {
    console.error('Identity security event was not persisted.', {
      eventType: event.eventType,
      reason: error instanceof Error || error instanceof DOMException ? error.name : 'UnknownError',
    });
  }
}
