'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import type { PricingProblem, PricingResult } from '@/lib/pricing-admin-client';

const apiBase = '/api/admin/pricing/';

// Browser-only: the console calls the same-origin proxy; a transport failure becomes an explicit PRICING_UNAVAILABLE state.
export async function pricingCall<T>(
  method: 'GET' | 'POST' | 'PUT',
  path: string,
  body?: unknown
): Promise<PricingResult<T>> {
  const headers: Record<string, string> = { Accept: 'application/json', 'X-Correlation-ID': crypto.randomUUID() };
  const init: RequestInit = { method, headers, cache: 'no-store', credentials: 'same-origin' };
  if (method !== 'GET') {
    headers['Idempotency-Key'] = crypto.randomUUID();
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body ?? {});
  }
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, init);
  } catch {
    return { ok: false, status: 0, problem: { code: 'PRICING_UNAVAILABLE' } };
  }
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (response.ok) return { ok: true, status: response.status, data: payload as T, etag: response.headers.get('etag') };
  const problem = (payload !== null && typeof payload === 'object' ? payload : {}) as PricingProblem;
  return { ok: false, status: response.status, problem };
}
