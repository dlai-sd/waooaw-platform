// Implements: architecture/reference/components/identity-boundary.md §7 Canonical Public API
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { NextRequest, NextResponse } from 'next/server';
import { createIdentityApi, identityProblem } from '@/lib/api/identity';
import { accessTokenFromRequest } from '@/lib/server-auth';

type CommandBody = Record<string, unknown>;
class InvalidRequestError extends Error {}

function requiredString(body: CommandBody, name: string): string {
  const value = body[name];
  if (typeof value !== 'string' || value.length === 0) throw new InvalidRequestError();
  return value;
}

export async function POST(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ code: 'IDENTITY_SESSION_REQUIRED', title: 'Secure sign in is required.' }, { status: 401 });
  try {
    const body = await request.json() as CommandBody;
    const action = requiredString(body, 'action');
    const idempotencyKey = requiredString(body, 'idempotencyKey');
    const api = createIdentityApi(accessToken);
    if (action === 'mobile-start') {
      return NextResponse.json(await api.startAccountMobileVerification({ idempotencyKey, startMobileVerificationRequest: { mobile: requiredString(body, 'mobile') } }));
    }
    if (action === 'mobile-confirm') {
      return NextResponse.json(await api.confirmAccountMobileVerification({ idempotencyKey, confirmIdentityVerificationRequest: { challengeId: requiredString(body, 'challengeId'), code: requiredString(body, 'code') } }));
    }
    return NextResponse.json({ code: 'IDENTITY_REQUEST_INVALID', title: 'Identity request is invalid.' }, { status: 400 });
  } catch (error) {
    if (error instanceof InvalidRequestError || error instanceof SyntaxError) return NextResponse.json({ code: 'IDENTITY_REQUEST_INVALID', title: 'Identity request is invalid.' }, { status: 400 });
    const problem = await identityProblem(error);
    return NextResponse.json(problem.body, { status: problem.status });
  }
}