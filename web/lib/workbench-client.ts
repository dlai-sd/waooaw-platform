'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-023, C-059, C-063, ADR-051

import type { WorkbenchProblem } from '@/lib/api/workbench-types';
import type { WorkbenchMessages } from '@/lib/workbench-i18n';

export type WorkbenchResult<T> =
  | { ok: true; status: number; data: T; version: string | null }
  | { ok: false; status: number; problem: WorkbenchProblem; strongAuthRequired: boolean };

const strongAuthDetail = 'strong sign-in';

function normalizeVersion(etag: string | null): string | null {
  const value = (etag ?? '').replace(/^W\//, '').replace(/"/g, '');
  return value.length > 0 ? value : null;
}

async function call<T>(relationshipId: string, path: string, init: RequestInit): Promise<WorkbenchResult<T>> {
  let response: Response;
  try {
    response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/workbench${path}`, {
      ...init,
      cache: 'no-store',
      credentials: 'same-origin',
    });
  } catch {
    return { ok: false, status: 0, problem: { code: 'WORKBENCH_UNAVAILABLE' }, strongAuthRequired: false };
  }
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (response.ok) {
    return {
      ok: true,
      status: response.status,
      data: body as T,
      version: normalizeVersion(response.headers.get('etag')),
    };
  }
  const problem = (body !== null && typeof body === 'object' ? body : {}) as WorkbenchProblem;
  return {
    ok: false,
    status: response.status,
    problem,
    strongAuthRequired: response.status === 403 && (problem.detail ?? '').toLowerCase().includes(strongAuthDetail),
  };
}

export function readWorkbench<T>(relationshipId: string, path = ''): Promise<WorkbenchResult<T>> {
  return call<T>(relationshipId, path, { method: 'GET', headers: { Accept: 'application/json' } });
}

// Each user action gets its own idempotency key, so a double submit of the same action replays instead of repeating.
export function sendWorkbenchCommand<T>(
  relationshipId: string,
  path: string,
  body: unknown,
  idempotencyKey: string = crypto.randomUUID()
): Promise<WorkbenchResult<T>> {
  return call<T>(relationshipId, path, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
      'X-Correlation-ID': crypto.randomUUID(),
    },
    body: JSON.stringify(body),
  });
}

export function problemText(
  copy: WorkbenchMessages,
  result: { problem: WorkbenchProblem; strongAuthRequired: boolean }
) {
  const code = result.problem.code;
  if (result.strongAuthRequired) return copy.strongAuth;
  return (code && copy.problems[code]) || copy.problems.WORKBENCH_UNAVAILABLE;
}
