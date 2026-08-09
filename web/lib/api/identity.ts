import 'server-only';

// Implements: architecture/reference/components/identity-boundary.md §7 Canonical Public API
// Constitutional basis: C-026 (Tenant Isolation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { IdentityApi } from '@/lib/api/generated/apis/IdentityApi';
import { Configuration, ResponseError } from '@/lib/api/generated/runtime';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export function createIdentityApi(accessToken: string): IdentityApi {
  return new IdentityApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
}

export async function identityProblem(error: unknown): Promise<{ status: number; body: unknown }> {
  if (error instanceof ResponseError) {
    const body = await error.response.json().catch(() => undefined);
    return {
      status: error.response.status,
      body: body ?? { code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' },
    };
  }
  return {
    status: 503,
    body: { code: 'IDENTITY_DEPENDENCY_UNAVAILABLE', title: 'Identity request could not be completed.' },
  };
}