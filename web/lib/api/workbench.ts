import 'server-only';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-04
// Constitutional basis: C-001, C-023, C-059, C-063, ADR-051

import { Configuration, ResponseError, WorkbenchApi } from '@/lib/api/generated/workbench-v1/src';
import { workbenchExperienceCapabilities } from '@/lib/api/workbench-capabilities';
import type { WorkbenchLoad, WorkbenchProjection, WorkbenchSnapshot } from '@/lib/api/workbench-types';
import { logServerFailure } from '@/lib/server-failure';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';
const init = { cache: 'no-store' } as const;

async function isDisabled(error: unknown): Promise<boolean> {
  if (!(error instanceof ResponseError) || error.response.status !== 404) return false;
  try {
    const body: unknown = await error.response.clone().json();
    return typeof body === 'object' && body !== null && 'code' in body && body.code === 'WORKBENCH_DISABLED';
  } catch (parseError) {
    logServerFailure('web.api.workbench.disabled_probe_failed', parseError);
    return false;
  }
}

async function optional<T>(read: () => Promise<{ raw: Response }>): Promise<T | null> {
  try {
    return (await (await read()).raw.json()) as T;
  } catch (error) {
    logServerFailure('web.api.workbench.section_failed', error);
    return null;
  }
}

// Never throws: a disabled flag, a failed read or an unreachable service each become an explicit state.
export async function getWorkbench(relationshipId: string, accessToken: string): Promise<WorkbenchLoad> {
  const api = new WorkbenchApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
  const capabilities = { relationshipId, xExperienceCapabilities: workbenchExperienceCapabilities };
  let projection: WorkbenchProjection;
  let version: string;
  try {
    const response = await api.getWorkbenchRaw(capabilities, init);
    projection = (await response.raw.json()) as WorkbenchProjection;
    version = (response.raw.headers.get('etag') ?? '').replace(/^W\//, '').replace(/"/g, '');
  } catch (error) {
    if (await isDisabled(error)) return { state: 'disabled' };
    logServerFailure('web.api.workbench.projection_failed', error);
    return { state: 'unavailable' };
  }
  if (version.length === 0) {
    logServerFailure('web.api.workbench.version_missing', new Error('The workbench projection carried no ETag.'));
    return { state: 'unavailable' };
  }

  const [goals, plan, capabilityList, wallet, evidence, workItems] = await Promise.all([
    optional<WorkbenchSnapshot['goals'] & object>(() => api.listWorkbenchGoalsRaw({ relationshipId }, init)),
    optional<WorkbenchSnapshot['plan'] & object>(() => api.getCurrentWorkbenchPlanRaw(capabilities, init)),
    optional<WorkbenchSnapshot['capabilities'] & object>(() => api.listWorkbenchCapabilitiesRaw(capabilities, init)),
    projection.audience === 'beneficiary'
      ? Promise.resolve(null)
      : optional<WorkbenchSnapshot['wallet'] & object>(() => api.getWorkbenchWalletRaw({ relationshipId }, init)),
    optional<WorkbenchSnapshot['evidence'] & object>(() => api.listWorkbenchEvidenceRaw({ relationshipId }, init)),
    optional<WorkbenchSnapshot['workItems'] & object>(() => api.listWorkbenchWorkItemsRaw({ relationshipId }, init)),
  ]);
  return {
    state: 'available',
    snapshot: { projection, version, goals, plan, capabilities: capabilityList, wallet, evidence, workItems },
  };
}
