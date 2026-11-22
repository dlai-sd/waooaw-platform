'use client';

// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import type { ProviderProblem, ProviderResult } from '@/lib/provider-admin-client';

const apiBase = '/api/admin/providers';

// Browser-only: calls the same-origin proxy; a transport failure becomes an explicit PROVIDER_VAULT_UNAVAILABLE state.
export async function providerCall<T>(
  method: 'GET' | 'POST',
  path: string,
  body?: unknown
): Promise<ProviderResult<T>> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-Correlation-ID': crypto.randomUUID(),
  };
  const init: RequestInit = {
    method,
    headers,
    cache: 'no-store',
    credentials: 'same-origin',
  };
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body ?? {});
  }
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, init);
  } catch {
    return {
      ok: false,
      status: 0,
      problem: { code: 'PROVIDER_VAULT_UNAVAILABLE' },
    };
  }
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (response.ok) return { ok: true, status: response.status, data: payload as T };
  const problem = (payload !== null && typeof payload === 'object' ? payload : {}) as ProviderProblem;
  return { ok: false, status: response.status, problem };
}
