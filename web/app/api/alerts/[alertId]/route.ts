import { NextRequest, NextResponse } from 'next/server';
import { NotificationsApi } from '@/lib/api/generated/apis/NotificationsApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export async function POST(request: NextRequest, { params }: { params: Promise<{ alertId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });

  const { alertId } = await params;
  const body = await request.json() as { action?: string; expectedAlertVersion?: string; idempotencyKey?: string };
  if (!['read', 'acknowledge'].includes(body.action ?? '') || !body.expectedAlertVersion || !body.idempotencyKey) {
    return NextResponse.json({ title: 'Alert request is invalid.' }, { status: 400 });
  }

  const api = new NotificationsApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
  const operation = {
    alertId,
    idempotencyKey: body.idempotencyKey,
    customerAlertMutationRequestV1: { schemaVersion: '1.0.0' as const, expectedAlertVersion: body.expectedAlertVersion },
  };
  try {
    const alert = body.action === 'acknowledge'
      ? await api.acknowledgeCustomerAlert(operation, { cache: 'no-store' })
      : await api.markCustomerAlertRead(operation, { cache: 'no-store' });
    return NextResponse.json(alert, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    if (error instanceof ResponseError) {
      const payload = await error.response.json().catch(() => ({ title: 'Alert update could not be completed.' }));
      return NextResponse.json(payload, { status: error.response.status, headers: { 'Cache-Control': 'no-store' } });
    }
    return NextResponse.json({ title: 'Alert update could not be completed.' }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
}