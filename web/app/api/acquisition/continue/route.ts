// Implements: WC-096 §4.3 Marketplace And Disclosure
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { type NextRequest, NextResponse } from 'next/server';
import { ProfessionalsApi } from '@/lib/api/generated/apis/ProfessionalsApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { accessTokenFromRequest } from '@/lib/server-auth';

type AcquisitionCommand = {
  professionalType?: string;
  professionalVersion?: string;
  intent?: string;
  disclosureRevision?: string;
  termsVersion?: string;
  idempotencyKey?: string;
};

const versionPattern = /^\d+\.\d+\.\d+$/;
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function POST(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });

  const body = (await request.json()) as AcquisitionCommand;
  if (
    !body.professionalType ||
    !/^[A-Z][A-Z0-9_]{0,63}$/.test(body.professionalType) ||
    !body.professionalVersion ||
    !versionPattern.test(body.professionalVersion) ||
    (body.intent !== 'trial' && body.intent !== 'hire') ||
    !body.disclosureRevision ||
    !versionPattern.test(body.disclosureRevision) ||
    !body.termsVersion ||
    !/^\d{4}-\d{2}-\d{2}$/.test(body.termsVersion) ||
    !body.idempotencyKey ||
    !uuidPattern.test(body.idempotencyKey)
  ) {
    return NextResponse.json({ title: 'Acquisition continuation is invalid.' }, { status: 400 });
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
        xCorrelationID: crypto.randomUUID(),
        continueAcquisitionRequest: {
          professionalType: body.professionalType,
          professionalVersion: body.professionalVersion,
          intent: body.intent.toUpperCase() as 'TRIAL' | 'HIRE',
          disclosureRevision: body.disclosureRevision,
          termsVersion: new Date(`${body.termsVersion}T00:00:00.000Z`),
          acceptance: 'ACCEPT_DISCLOSURE',
        },
      },
      { cache: 'no-store' }
    );
    return NextResponse.json(result, { headers: { 'Cache-Control': 'no-store' } });
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
