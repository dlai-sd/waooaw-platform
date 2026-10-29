import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { NextResponse } from 'next/server';
import { getServerAccessToken } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

async function POSTHandler(request: Request, { params }: { params: Promise<{ relationshipId: string }> }) {
  const token = await getServerAccessToken();
  if (!token) return NextResponse.json({ title: 'Authentication required' }, { status: 401 });
  const { relationshipId } = await params;
  const parsed = await readRequestJson(request);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
    return NextResponse.json({ title: 'Export request is invalid.' }, { status: 400 });
  const body = parsed as Record<string, unknown>;
  const root = `${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/workspace/evidence-exports`;
  const created = await fetch(root, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': crypto.randomUUID(),
    },
    body: JSON.stringify({ schemaVersion: '1.0', purpose: body.purpose }),
    cache: 'no-store',
  });
  if (!created.ok) return NextResponse.json(await created.json(), { status: created.status });
  const receipt = await created.json();
  const outcome = await fetch(`${root}/${encodeURIComponent(receipt.exportId)}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });
  return NextResponse.json(await outcome.json(), { status: outcome.status });
}

export const POST = withServerFailureBoundary(
  'web.relationships.relationshipid.evidence.export.post_failed',
  POSTHandler
);
