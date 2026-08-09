// Implements: architecture/reference/ux/wc-034-implementation-decomposition.md §F2
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { NextRequest, NextResponse } from 'next/server';
import { createIdentityApi, identityProblem } from '@/lib/api/identity';
import { accessTokenFromRequest } from '@/lib/server-auth';

type CommandBody = Record<string, unknown> & { action?: unknown };

class InvalidRequestError extends Error {}

function requiredString(body: CommandBody, name: string): string {
  const value = body[name];
  if (typeof value !== 'string' || value.length === 0) throw new InvalidRequestError(`Invalid ${name}`);
  return value;
}

export async function POST(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) {
    return NextResponse.json({ code: 'IDENTITY_SESSION_REQUIRED', title: 'Secure sign in is required.' }, { status: 401 });
  }

  try {
    const body = await request.json() as CommandBody;
    const api = createIdentityApi(accessToken);
    const action = requiredString(body, 'action');
    const idempotencyKey = requiredString(body, 'idempotencyKey');
    const registrationId = action === 'start' ? undefined : requiredString(body, 'registrationId');

    switch (action) {
      case 'start':
        return NextResponse.json(await api.startIdentityRegistration({
          idempotencyKey,
          startIdentityRegistrationRequest: { languagePreference: requiredString(body, 'languagePreference') },
        }));
      case 'profile':
        return NextResponse.json(await api.updateIdentityRegistrationProfile({
          registrationId: registrationId!,
          idempotencyKey,
          identityRegistrationProfileRequest: {
            displayName: requiredString(body, 'displayName'),
            businessName: requiredString(body, 'businessName'),
            businessDomain: requiredString(body, 'businessDomain'),
            languagePreference: requiredString(body, 'languagePreference'),
          },
        }));
      case 'email-start':
        return NextResponse.json(await api.startIdentityEmailVerification({
          registrationId: registrationId!,
          idempotencyKey,
          startEmailVerificationRequest: { email: requiredString(body, 'email') },
        }));
      case 'email-confirm':
        return NextResponse.json(await api.confirmIdentityEmailVerification({
          registrationId: registrationId!,
          idempotencyKey,
          confirmIdentityVerificationRequest: {
            challengeId: requiredString(body, 'challengeId'),
            code: requiredString(body, 'code'),
          },
        }));
      case 'mobile-start':
        return NextResponse.json(await api.startIdentityMobileVerification({
          registrationId: registrationId!,
          idempotencyKey,
          startMobileVerificationRequest: { mobile: requiredString(body, 'mobile') },
        }));
      case 'mobile-confirm':
        return NextResponse.json(await api.confirmIdentityMobileVerification({
          registrationId: registrationId!,
          idempotencyKey,
          confirmIdentityVerificationRequest: {
            challengeId: requiredString(body, 'challengeId'),
            code: requiredString(body, 'code'),
          },
        }));
      case 'complete':
        return NextResponse.json(await api.completeIdentityRegistration({ registrationId: registrationId!, idempotencyKey }));
      default:
        return NextResponse.json({ code: 'IDENTITY_REQUEST_INVALID', title: 'Identity request is invalid.' }, { status: 400 });
    }
  } catch (error) {
    if (error instanceof InvalidRequestError || error instanceof SyntaxError) {
      return NextResponse.json({ code: 'IDENTITY_REQUEST_INVALID', title: 'Identity request is invalid.' }, { status: 400 });
    }
    const problem = await identityProblem(error);
    return NextResponse.json(problem.body, { status: problem.status });
  }
}