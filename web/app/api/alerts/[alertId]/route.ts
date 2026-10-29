import { logServerFailure, readServerResponse } from '@/lib/server-failure';
import { withServerFailureBoundary, readRequestJson } from '@/lib/server-failure-boundary';
import { type NextRequest, NextResponse } from 'next/server';
import { NotificationsApi } from '@/lib/api/generated/apis/NotificationsApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';
import { accessTokenFromRequest } from '@/lib/server-auth';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

async function POSTHandler(request: NextRequest, { params }: { params: Promise<{ alertId: string }> }) {
  const accessToken = await accessTokenFromRequest(request);
  if (!accessToken) return NextResponse.json({ title: 'Secure sign in is required.' }, { status: 401 });

  const { alertId } = await params;
  const body = (await readRequestJson(request)) as {
    action?: string;
    expectedAlertVersion?: string;
    idempotencyKey?: string;
  };
  if (!['read', 'acknowledge'].includes(body.action ?? '') || !body.expectedAlertVersion || !body.idempotencyKey) {
    return NextResponse.json({ title: 'Alert request is invalid.' }, { status: 400 });
  }

  const api = new NotificationsApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
  const operation = {
    alertId,
    idempotencyKey: body.idempotencyKey,
    customerAlertMutationRequestV1: {
      schemaVersion: '1.0.0' as const,
      expectedAlertVersion: body.expectedAlertVersion,
    },
  };
  try {
    const alert =
      body.action === 'acknowledge'
        ? await api.acknowledgeCustomerAlert(operation, { cache: 'no-store' })
        : await api.markCustomerAlertRead(operation, { cache: 'no-store' });
    return NextResponse.json(alert, {
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    logServerFailure('web.alerts.alertid.request_failed', error);
    if (error instanceof ResponseError) {
      const payload = await readServerResponse(error.response, 'web.alerts.alertid.response_invalid', {
        title: 'Alert update could not be completed.',
      });
      return NextResponse.json(payload, {
        status: error.response.status,
        headers: { 'Cache-Control': 'no-store' },
      });
    }
    return NextResponse.json(
      { title: 'Alert update could not be completed.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

export const POST = withServerFailureBoundary('web.alerts.alertid.post_failed', POSTHandler);
