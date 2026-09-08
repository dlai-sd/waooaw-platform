import 'server-only';

import { NotificationsApi } from '@/lib/api/generated/apis/NotificationsApi';
import type { CustomerAlertPageV1 } from '@/lib/api/generated/models/CustomerAlertPageV1';
import { Configuration } from '@/lib/api/generated/runtime';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

function createNotificationsApi(accessToken: string): NotificationsApi {
  return new NotificationsApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
}

export async function listCustomerAlerts(
  accessToken: string,
  cursor?: string,
): Promise<CustomerAlertPageV1> {
  return createNotificationsApi(accessToken).listCustomerAlerts(
    { cursor, limit: 40 },
    { cache: 'no-store' },
  );
}