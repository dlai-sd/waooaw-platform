// Implements: WC-096 §4.3 Marketplace And Disclosure
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { persistAcquisitionIntent } from '@/lib/api/acquisition-intent';
import { ProfessionalsApi } from '@/lib/api/generated/apis/ProfessionalsApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { getIdentitySession } from '@/lib/api/identity';
import { createMyAgentsSelection, myAgentsSelectionCookie } from '@/lib/api/my-agents-selection';
import { withJourneyTrace } from '@/lib/journey-telemetry';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { type NextRequest, NextResponse } from 'next/server';

type AcquisitionCommand = {
  professionalType?: string;
  professionalVersion?: string;
  intent?: string;
  disclosureRevision?: string;
  termsVersion?: string;
  idempotencyKey?: string;
  contractAcceptance?: string;
};

const versionPattern = /^\d+\.\d+\.\d+$/;
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

async function continueTrial(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });

  const body = (await request.json()) as AcquisitionCommand;
  if (
    !body.professionalType ||
    !/^[A-Z][A-Z0-9_]{0,63}$/.test(body.professionalType) ||
    !body.professionalVersion ||
    !versionPattern.test(body.professionalVersion) ||
    body.intent !== 'trial' ||
    !body.disclosureRevision ||
    !versionPattern.test(body.disclosureRevision) ||
    !body.termsVersion ||
    !/^\d{4}-\d{2}-\d{2}$/.test(body.termsVersion) ||
    !body.idempotencyKey ||
    !uuidPattern.test(body.idempotencyKey) ||
    body.contractAcceptance !== 'ACCEPT_EMPLOYMENT_CONTRACT'
  ) {
    return NextResponse.json({ title: 'Acquisition continuation is invalid.' }, { status: 400 });
  }

  const persisted = await persistAcquisitionIntent(accessToken, body.idempotencyKey, {
    professionalType: body.professionalType,
    professionalVersion: body.professionalVersion,
    intent: 'TRIAL',
    disclosureRevision: body.disclosureRevision,
    termsVersion: body.termsVersion,
    acceptance: body.contractAcceptance,
  });
  if (!persisted.ok) {
    const payload = await persisted.json().catch(() => ({ title: 'Acquisition intent could not be saved.' }));
    return NextResponse.json(payload, {
      status: persisted.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  }

  const identity = await getIdentitySession(accessToken);
  if (identity.kind === 'registration-required') {
    return NextResponse.json(
      { code: 'REGISTRATION_REQUIRED', title: 'Complete registration before starting a professional.' },
      { status: 409, headers: { 'Cache-Control': 'no-store' } }
    );
  }
  if (identity.kind !== 'ready') {
    const status = identity.kind === 'unauthorized' || identity.kind === 'expired' ? 401 : 403;
    return NextResponse.json(
      {
        code: identity.kind === 'forbidden' ? identity.code : undefined,
        title: status === 401 ? 'Secure sign in is required.' : 'Acquisition is not permitted.',
      },
      { status, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  const api = new ProfessionalsApi(
    new Configuration({
      basePath: process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001',
      accessToken,
    })
  );
  try {
    const result = await api.continueAcquisition(
      {
        idempotencyKey: body.idempotencyKey,
        xCorrelationID: body.idempotencyKey,
        continueAcquisitionRequest: {
          professionalType: body.professionalType,
          professionalVersion: body.professionalVersion,
          intent: body.intent.toUpperCase() as 'TRIAL' | 'HIRE',
          disclosureRevision: body.disclosureRevision,
          termsVersion: new Date(`${body.termsVersion}T00:00:00.000Z`),
          acceptance: body.contractAcceptance,
        },
      },
      { cache: 'no-store' }
    );
    const selection = await createMyAgentsSelection(accessToken, result.relationshipId, 'TRIAL_STARTED');
    const response = NextResponse.json(
      { ...result, resumePath: '/professionals/mine' },
      { headers: { 'Cache-Control': 'no-store' } }
    );
    response.cookies.set(myAgentsSelectionCookie, selection.handle, {
      expires: new Date(selection.expiresAt),
      httpOnly: true,
      path: '/professionals/mine',
      sameSite: 'strict',
      secure: true,
    });
    return response;
  } catch (error) {
    if (error instanceof ResponseError) {
      const payload = await error.response.json().catch(() => ({ title: 'Acquisition could not continue.' }));
      return NextResponse.json(payload, { status: error.response.status, headers: { 'Cache-Control': 'no-store' } });
    }
    return NextResponse.json(
      { title: 'Acquisition could not continue.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

export const POST = (request: NextRequest) => withJourneyTrace('trial.continue', () => continueTrial(request));
