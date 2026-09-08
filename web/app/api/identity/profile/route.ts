import { NextRequest, NextResponse } from 'next/server';
import { createIdentityApi, identityProblem } from '@/lib/api/identity';
import { accessTokenFromRequest } from '@/lib/server-auth';

export async function PUT(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const body = await request.json() as { displayName?: string; organizationDisplayName?: string; idempotencyKey?: string };
  if (!body.displayName?.trim() || !body.organizationDisplayName?.trim() || !body.idempotencyKey) {
    return NextResponse.json({ title: 'Profile fields are required.' }, { status: 400 });
  }
  try {
    const profile = await createIdentityApi(accessToken).updateCustomerProfile({
      idempotencyKey: body.idempotencyKey,
      updateCustomerProfileRequestV1: { schemaVersion: '1.0.0', displayName: body.displayName.trim(), organizationDisplayName: body.organizationDisplayName.trim() },
    }, { cache: 'no-store' });
    return NextResponse.json(profile, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    const problem = await identityProblem(error);
    return NextResponse.json(problem.body, { status: problem.status, headers: { 'Cache-Control': 'no-store' } });
  }
}