// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R007, WC149-R008
// Constitutional basis: C-026, C-059, C-063, C-083

import type { NextRequest } from 'next/server';
import { completeMetaCallback } from '@/lib/provider-connections-server';
import { accessTokenFromRequest } from '@/lib/server-auth';
import { withServerFailureBoundary } from '@/lib/server-failure-boundary';

// The public redirect URI registered in the Meta app: /api/provider-connections/meta/callback
async function handle(request: NextRequest) {
  return completeMetaCallback(request, await accessTokenFromRequest(request));
}

export const GET = withServerFailureBoundary('web.provider_connections.callback_get_failed', handle);
