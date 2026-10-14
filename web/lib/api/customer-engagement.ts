import 'server-only';

// Implements: WC-121 Components 01-06 canonical customer engagement projection
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063

import { RelationshipWorkspaceApi } from '@/lib/api/generated/apis/RelationshipWorkspaceApi';
import type { CustomerEngagementProgressV1 } from '@/lib/api/generated/models/CustomerEngagementProgressV1';
import { Configuration } from '@/lib/api/generated/runtime';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export async function getCustomerEngagementProgress(
  relationshipId: string,
  accessToken: string
): Promise<CustomerEngagementProgressV1> {
  return new RelationshipWorkspaceApi(
    new Configuration({ basePath: businessPlatformUrl, accessToken })
  ).getCustomerEngagementProgress({ relationshipId }, { cache: 'no-store' });
}
