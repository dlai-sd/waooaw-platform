// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S12
// Constitutional basis: C-002, C-005, C-059, C-063

import { type NextRequest, NextResponse } from 'next/server';
import {
  persistWebIdentitySecurityEvent,
  type WebIdentityProviderClass,
  type WebIdentitySecurityEvent,
} from '@/lib/identity-security-events';

const providerClasses = new Set<WebIdentityProviderClass>(['GOOGLE', 'FACEBOOK', 'APPLE', 'EMAIL', 'UNKNOWN']);
const transitionEvents = {
  ROUTE_REQUESTED: ['AUTHENTICATION_START', 'ATTEMPTED', 'AUTH_ROUTE_REQUESTED'],
  BROKER_REDIRECT_REQUESTED: ['PROVIDER_HANDOFF', 'ATTEMPTED', 'BROKER_REDIRECT_REQUESTED'],
  PROVIDER_CANCELLED: ['AUTHENTICATION_START', 'CANCELLED', 'CUSTOMER_CANCELLED'],
  BROKER_LAUNCH_FAILED: ['PROVIDER_HANDOFF', 'FAILED', 'BROKER_LAUNCH_FAILED'],
  SESSION_RESOLVED: ['CALLBACK_SUCCESS', 'SUCCEEDED', 'BROKER_CALLBACK_VALID'],
  CALLBACK_FAILED: ['CALLBACK_FAILURE', 'FAILED', 'BROKER_CALLBACK_FAILED'],
  ACCOUNT_SWITCH_REQUESTED: ['ACCOUNT_SWITCH', 'ATTEMPTED', 'CUSTOMER_REQUESTED'],
  ACCOUNT_SWITCH_COMPLETED: ['ACCOUNT_SWITCH', 'SUCCEEDED', 'PRIOR_SESSION_REVOKED'],
  ACCOUNT_SWITCH_FAILED: ['ACCOUNT_SWITCH', 'FAILED', 'SESSION_REVOCATION_UNCONFIRMED'],
} as const;

function isSameOrigin(request: NextRequest) {
  const applicationOrigin = new URL(process.env.NEXTAUTH_URL ?? request.nextUrl.origin).origin;
  const origin = request.headers.get('origin');
  if (origin) return origin === applicationOrigin;
  return request.headers.get('sec-fetch-site') === 'same-origin';
}

export async function POST(request: NextRequest) {
  if (!isSameOrigin(request))
    return NextResponse.json({ code: 'IDENTITY_ACTION_DENIED' }, { status: 403 });

  let input: { correlationId?: unknown; stage?: unknown; providerClass?: unknown };
  try {
    input = (await request.json()) as typeof input;
  } catch {
    return NextResponse.json({ code: 'IDENTITY_EVENT_INVALID' }, { status: 400 });
  }
  if (
    typeof input.correlationId !== 'string' ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(input.correlationId) ||
    typeof input.stage !== 'string' ||
    !(input.stage in transitionEvents) ||
    typeof input.providerClass !== 'string' ||
    !providerClasses.has(input.providerClass as WebIdentityProviderClass)
  )
    return NextResponse.json({ code: 'IDENTITY_EVENT_INVALID' }, { status: 400 });

  const [eventType, outcome, reasonCode] = transitionEvents[input.stage as keyof typeof transitionEvents];
  try {
    await persistWebIdentitySecurityEvent({
      correlationId: input.correlationId,
      eventType,
      providerClass: input.providerClass as WebIdentityProviderClass,
      outcome,
      reasonCode,
      assuranceClass: eventType === 'CALLBACK_SUCCESS' ? 'AAL2' : 'ANONYMOUS',
    } as WebIdentitySecurityEvent);
    return new NextResponse(null, { status: 204 });
  } catch {
    return NextResponse.json({ code: 'IDENTITY_EVENT_UNAVAILABLE' }, { status: 503 });
  }
}