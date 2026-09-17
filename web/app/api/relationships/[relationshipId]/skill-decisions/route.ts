import { NextRequest, NextResponse } from 'next/server';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export async function GET(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  const response = await fetch(`${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/evaluation`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: 'no-store',
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ title: 'Accepted Skills are unavailable.' }));
    return NextResponse.json(payload, { status: response.status, headers: { 'Cache-Control': 'no-store' } });
  }
  const payload = await response.json() as { skills?: unknown };
  if (!Array.isArray(payload.skills)) {
    return NextResponse.json({ title: 'Accepted Skills are unavailable.' }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
  const skills = payload.skills.flatMap((value) => {
    if (!value || typeof value !== 'object') return [];
    const skill = value as Record<string, unknown>;
    return skill.status === 'ACCEPTED' && typeof skill.skillId === 'string' && typeof skill.skillVersion === 'string'
      ? [{ skillId: skill.skillId, skillVersion: skill.skillVersion }]
      : [];
  });
  return NextResponse.json({ skills }, { headers: { 'Cache-Control': 'no-store' } });
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const { relationshipId } = await params;
  const body = await request.json() as { idempotencyKey?: string; command?: unknown };
  if (!body.idempotencyKey || !body.command) return NextResponse.json({ title: 'Skill decision is invalid.' }, { status: 400 });
  const response = await fetch(`${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/workspace/commands`, { method: 'POST', headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json', 'Idempotency-Key': body.idempotencyKey }, body: JSON.stringify(body.command), cache: 'no-store' });
  const payload = await response.json().catch(() => ({ title: 'Skill decision could not be recorded.' }));
  return NextResponse.json(payload, { status: response.status, headers: { 'Cache-Control': 'no-store' } });
}