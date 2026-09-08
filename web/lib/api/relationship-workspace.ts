import 'server-only';

import { ConfigurationApi } from '@/lib/api/generated/apis/ConfigurationApi';
import { RelationshipWorkspaceApi } from '@/lib/api/generated/apis/RelationshipWorkspaceApi';
import type { RelationshipAttentionPageV1 } from '@/lib/api/generated/models/RelationshipAttentionPageV1';
import type { RelationshipBusinessOutcomesV1 } from '@/lib/api/generated/models/RelationshipBusinessOutcomesV1';
import type { RelationshipConfigurationV1 } from '@/lib/api/generated/models/RelationshipConfigurationV1';
import type { RelationshipEvidencePageV1 } from '@/lib/api/generated/models/RelationshipEvidencePageV1';
import type { RelationshipGoalsV1 } from '@/lib/api/generated/models/RelationshipGoalsV1';
import type { RelationshipOperationsV1 } from '@/lib/api/generated/models/RelationshipOperationsV1';
import type { RelationshipPlanV1 } from '@/lib/api/generated/models/RelationshipPlanV1';
import type { RelationshipResultsV1 } from '@/lib/api/generated/models/RelationshipResultsV1';
import type { RelationshipRightsControlsV1 } from '@/lib/api/generated/models/RelationshipRightsControlsV1';
import type { RelationshipUsageBudgetV1 } from '@/lib/api/generated/models/RelationshipUsageBudgetV1';
import type { RelationshipWorkPageV1 } from '@/lib/api/generated/models/RelationshipWorkPageV1';
import type { RelationshipWorkspaceV1 } from '@/lib/api/generated/models/RelationshipWorkspaceV1';
import { Configuration } from '@/lib/api/generated/runtime';

export interface RelationshipWorkspaceViews {
  workspace: RelationshipWorkspaceV1;
  configuration: RelationshipConfigurationV1;
  goals: RelationshipGoalsV1;
  businessOutcomes: RelationshipBusinessOutcomesV1;
  operations: RelationshipOperationsV1;
  plan: RelationshipPlanV1;
  attention: RelationshipAttentionPageV1;
  work: RelationshipWorkPageV1;
  results: RelationshipResultsV1;
  usageBudget: RelationshipUsageBudgetV1;
  rightsControls: RelationshipRightsControlsV1;
  evidence: RelationshipEvidencePageV1;
}

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export async function getRelationshipWorkspaceViews(
  relationshipId: string,
  accessToken: string
): Promise<RelationshipWorkspaceViews> {
  const clientConfiguration = new Configuration({ basePath: businessPlatformUrl, accessToken });
  const workspaceApi = new RelationshipWorkspaceApi(clientConfiguration);
  const configurationApi = new ConfigurationApi(clientConfiguration);
  const request = { relationshipId };
  const noStore = { cache: 'no-store' as const };
  const [workspace, configuration, goals, businessOutcomes, operations, plan, attention, work, results, usageBudget, rightsControls, evidence] = await Promise.all([
    workspaceApi.getRelationshipWorkspace(request, noStore),
    configurationApi.getRelationshipConfiguration(request, noStore),
    workspaceApi.getRelationshipGoals(request, noStore),
    workspaceApi.getRelationshipBusinessOutcomes(request, noStore),
    workspaceApi.getRelationshipOperations(request, noStore),
    workspaceApi.getRelationshipPlan(request, noStore),
    workspaceApi.getRelationshipAttention({ ...request, limit: 40 }, noStore),
    workspaceApi.getRelationshipWork(request, noStore),
    workspaceApi.getRelationshipResults(request, noStore),
    workspaceApi.getRelationshipUsageBudget(request, noStore),
    workspaceApi.getRelationshipRightsControls(request, noStore),
    workspaceApi.listRelationshipEvidence({ ...request, limit: 40 }, noStore),
  ]);
  return { workspace, configuration, goals, businessOutcomes, operations, plan, attention, work, results, usageBudget, rightsControls, evidence };
}