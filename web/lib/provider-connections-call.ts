'use client';

// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R010
// Constitutional basis: C-026, C-059, C-063, C-083

import type { ConnectionProblem, ConnectionResult } from '@/lib/provider-connections-client';

const apiBase = '/api/provider-connections';

// Browser-only: calls the same-origin proxy; a transport failure becomes an explicit CONNECTION_UNAVAILABLE state.
export async function connectionCall<T>(
  method: 'GET' | 'POST',
  path: string,
  body?: unknown
): Promise<ConnectionResult<T>> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-Correlation-ID': crypto.randomUUID(),
  };
  const init: RequestInit = { method, headers, cache: 'no-store', credentials: 'same-origin' };
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body ?? {});
  }
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, init);
  } catch {
    return { ok: false, status: 0, problem: { code: 'CONNECTION_UNAVAILABLE' } };
  }
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (response.ok) return { ok: true, status: response.status, data: payload as T };
  const problem = (payload !== null && typeof payload === 'object' ? payload : {}) as ConnectionProblem;
  return { ok: false, status: response.status, problem };
}
