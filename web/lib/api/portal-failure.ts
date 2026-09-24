import 'server-only';

import { FetchError, ResponseError } from '@/lib/api/generated/runtime';

export type PortalSurface = 'HOME' | 'MARKETPLACE' | 'MY_AGENTS';

export interface PortalFailure {
  correlationId: string;
  reasonCode: 'AUTHORIZATION_REJECTED' | 'RESPONSE_INVALID' | 'SERVICE_UNAVAILABLE' | 'SERVICE_UNREACHABLE';
  statusClass: string;
}

const safeCorrelationId = /^[A-Za-z0-9-]{1,64}$/;

async function responseCorrelationId(response: Response): Promise<string | undefined> {
  const header = response.headers.get('x-correlation-id');
  if (header && safeCorrelationId.test(header)) return header;
  try {
    const body = await response.clone().json() as { correlationId?: unknown };
    return typeof body.correlationId === 'string' && safeCorrelationId.test(body.correlationId)
      ? body.correlationId
      : undefined;
  } catch {
    return undefined;
  }
}

export async function describePortalFailure(error: unknown, surface: PortalSurface): Promise<PortalFailure> {
  let correlationId = crypto.randomUUID();
  let reasonCode: PortalFailure['reasonCode'] = 'RESPONSE_INVALID';
  let statusClass = 'none';

  if (error instanceof ResponseError) {
    correlationId = (await responseCorrelationId(error.response)) ?? correlationId;
    statusClass = `${Math.floor(error.response.status / 100)}xx`;
    if (error.response.status === 401 || error.response.status === 403) reasonCode = 'AUTHORIZATION_REJECTED';
    else if (error.response.status >= 500) reasonCode = 'SERVICE_UNAVAILABLE';
  } else if (error instanceof FetchError) {
    reasonCode = 'SERVICE_UNREACHABLE';
  }

  console.error('Portal projection failed.', { correlationId, reasonCode, statusClass, surface });
  return { correlationId, reasonCode, statusClass };
}