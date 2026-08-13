// Implements: WC-065 WC065-05 generated BP-only Founder experience
// Constitutional basis: C-023, C-059, C-063

import { NextRequest, NextResponse } from 'next/server';
import { EmploymentApi } from '@/lib/api/generated/apis/EmploymentApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { accessTokenFromRequest } from '@/lib/server-auth';

type OfferabilityCommand = {
  idempotencyKey?: string;
  relationshipId?: string;
  offeringId?: string;
  agentType?: string;
  bundleTier?: string;
  proposedPricePaise?: number;
};

export async function POST(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ code: 'UNAUTHENTICATED' }, { status: 401 });
  const body = (await request.json()) as OfferabilityCommand;
  if (!body.idempotencyKey || !body.relationshipId || !body.offeringId || !body.agentType || !body.bundleTier || !body.proposedPricePaise) {
    return NextResponse.json({ code: 'OFFERABILITY_REQUEST_INVALID' }, { status: 400 });
  }
  const api = new EmploymentApi(
    new Configuration({ basePath: process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001', accessToken }),
  );
  try {
    const decision = await api.evaluateRelationshipOfferability({
      relationshipId: body.relationshipId,
      idempotencyKey: body.idempotencyKey,
      xCorrelationID: crypto.randomUUID(),
      evaluateRelationshipOfferabilityRequest: {
        schemaVersion: '1.0',
        offeringId: body.offeringId,
        agentType: body.agentType,
        bundleTier: body.bundleTier,
        proposedPricePaise: body.proposedPricePaise,
      },
    });
    return NextResponse.json(decision);
  } catch (error) {
    if (error instanceof ResponseError) {
      const payload = await error.response.json().catch(() => ({ code: 'OFFERABILITY_RESPONSE_UNREADABLE' }));
      return NextResponse.json(payload, { status: error.response.status });
    }
    return NextResponse.json({ code: 'OFFERABILITY_UNAVAILABLE' }, { status: 503 });
  }
}