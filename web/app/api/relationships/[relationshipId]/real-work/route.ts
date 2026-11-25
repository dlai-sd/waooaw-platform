// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2 to DC-5 customer projections and DC-3 decisions (WC170-R005 to WC170-R008)
// Constitutional basis: C-001, C-023, C-059, C-063

import { type NextRequest, NextResponse } from 'next/server';
import { readServerResponse } from '@/lib/server-failure';
import { readRequestJson, withServerFailureBoundary } from '@/lib/server-failure-boundary';
import { accessTokenFromRequest } from '@/lib/server-auth';
import type { DecisionCommandKind, RealWorkSnapshot } from '@/lib/api/real-work-types';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const noStore = { 'Cache-Control': 'no-store' } as const;
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const digestPattern = /^[0-9a-f]{64}$/;
const acknowledgements: Record<DecisionCommandKind, string> = {
  ACCEPT_ARTIFACT_VERSION: 'I approve this exact version.',
  CONFIRM_SCOPE_BOUNDARY: 'This is within what the agent may do for me, and I name who may do it.',
};

function base(relationshipId: string) {
  return `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}`;
}

async function read<T>(url: string, accessToken: string): Promise<T | null> {
  const response = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` }, cache: 'no-store' });
  return response.ok ? ((await response.json()) as T) : null;
}

async function GETHandler(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  if (!uuidPattern.test(relationshipId)) return NextResponse.json({ title: 'Not found.' }, { status: 404 });
  const root = `${base(relationshipId)}/real-work`;
  const [artifacts, timeline, outcomes] = await Promise.all([
    read<RealWorkSnapshot['artifacts']>(`${root}/artifacts`, accessToken),
    read<RealWorkSnapshot['timeline']>(`${root}/timeline`, accessToken),
    read<RealWorkSnapshot['outcomes']>(`${root}/outcomes`, accessToken),
  ]);
  const snapshot: RealWorkSnapshot = { artifacts, timeline, outcomes };
  return NextResponse.json(snapshot, { headers: noStore });
}

// A customer decision is one of the two closed employment commands; the one command pipeline stays the only write path.
async function POSTHandler(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  const body = (await readRequestJson(request)) as {
    idempotencyKey?: string;
    kind?: DecisionCommandKind;
    artifactId?: string;
    artifactDigest?: string;
    commandContext?: { workspaceVersion?: string; manifestVersion?: string; decisionSpaceVersion?: number };
  };
  const context = body.commandContext;
  if (
    !uuidPattern.test(relationshipId) ||
    !body.idempotencyKey ||
    !uuidPattern.test(body.idempotencyKey) ||
    (body.kind !== 'ACCEPT_ARTIFACT_VERSION' && body.kind !== 'CONFIRM_SCOPE_BOUNDARY') ||
    !body.artifactId ||
    !uuidPattern.test(body.artifactId) ||
    !body.artifactDigest ||
    !digestPattern.test(body.artifactDigest) ||
    !context?.workspaceVersion ||
    !context.manifestVersion ||
    typeof context.decisionSpaceVersion !== 'number'
  )
    return NextResponse.json({ title: 'The decision is invalid.' }, { status: 400, headers: noStore });
  const command = {
    schemaVersion: '1.0',
    kind: body.kind,
    subjectRef: body.artifactId,
    expectedWorkspaceVersion: context.workspaceVersion,
    expectedManifestVersion: context.manifestVersion,
    expectedArtifactId: body.artifactId,
    expectedArtifactDigest: body.artifactDigest,
    ...(body.kind === 'CONFIRM_SCOPE_BOUNDARY' ? { expectedDecisionSpaceVersion: context.decisionSpaceVersion } : {}),
    acknowledgement: acknowledgements[body.kind],
  };
  const response = await fetch(`${base(relationshipId)}/workspace/employment/commands`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': body.idempotencyKey,
    },
    body: JSON.stringify(command),
    cache: 'no-store',
  });
  const payload = await readServerResponse(response, 'web.relationships.relationshipid.real.work.response_invalid', {
    title: 'The decision could not be recorded.',
  });
  return NextResponse.json(payload, { status: response.status, headers: noStore });
}

export const GET = withServerFailureBoundary('web.relationships.relationshipid.real.work.get_failed', GETHandler);
export const POST = withServerFailureBoundary('web.relationships.relationshipid.real.work.post_failed', POSTHandler);
