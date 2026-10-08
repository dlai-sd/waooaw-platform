import 'server-only';

import {
  Configuration,
  ConversationalEmploymentApi,
  ResponseError,
  type EmploymentWorkspaceV1,
} from '@/lib/api/generated/employment/src';

export type EmploymentWorkspaceLoad =
  | { state: 'available'; workspace: EmploymentWorkspaceV1 }
  | { state: 'unavailable'; reason: 'candidate-disabled' | 'not-established' };

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export async function getEmploymentWorkspace(
  relationshipId: string,
  accessToken: string
): Promise<EmploymentWorkspaceLoad> {
  const api = new ConversationalEmploymentApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
  try {
    const workspace = await api.getEmploymentWorkspace({ relationshipId }, { cache: 'no-store' });
    return { state: 'available', workspace };
  } catch (error) {
    if (error instanceof ResponseError && error.response.status === 503)
      return { state: 'unavailable', reason: 'candidate-disabled' };
    if (error instanceof ResponseError && error.response.status === 404)
      return { state: 'unavailable', reason: 'not-established' };
    throw error;
  }
}
