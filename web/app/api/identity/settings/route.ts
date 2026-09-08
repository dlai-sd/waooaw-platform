import { NextRequest, NextResponse } from 'next/server';
import type { UpdateCustomerSettingsRequestV1 } from '@/lib/api/generated/models/UpdateCustomerSettingsRequestV1';
import { createIdentityApi, identityProblem } from '@/lib/api/identity';
import { accessTokenFromRequest } from '@/lib/server-auth';

export async function PUT(request: NextRequest) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });
  const body = await request.json() as { settings?: UpdateCustomerSettingsRequestV1; idempotencyKey?: string };
  if (!body.settings || !body.idempotencyKey) return NextResponse.json({ title: 'Settings request is invalid.' }, { status: 400 });
  try {
    const settings = await createIdentityApi(accessToken).updateCustomerSettings({
      idempotencyKey: body.idempotencyKey,
      updateCustomerSettingsRequestV1: body.settings,
    }, { cache: 'no-store' });
    return NextResponse.json(settings, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    const problem = await identityProblem(error);
    return NextResponse.json(problem.body, { status: problem.status, headers: { 'Cache-Control': 'no-store' } });
  }
}