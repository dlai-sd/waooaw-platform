import { RelationshipWorkspaceV1FromJSON, type RelationshipWorkspaceV1 } from '@/lib/api/generated/models/RelationshipWorkspaceV1';
import { RelationshipPlanV1FromJSON, type RelationshipPlanV1 } from '@/lib/api/generated/models/RelationshipPlanV1';
import { RelationshipAttentionPageV1FromJSON, type RelationshipAttentionPageV1 } from '@/lib/api/generated/models/RelationshipAttentionPageV1';
import { RelationshipWorkPageV1FromJSON, type RelationshipWorkPageV1 } from '@/lib/api/generated/models/RelationshipWorkPageV1';
import { RelationshipResultsV1FromJSON, type RelationshipResultsV1 } from '@/lib/api/generated/models/RelationshipResultsV1';
import { RelationshipUsageBudgetV1FromJSON, type RelationshipUsageBudgetV1 } from '@/lib/api/generated/models/RelationshipUsageBudgetV1';
import { RelationshipRightsControlsV1FromJSON, type RelationshipRightsControlsV1 } from '@/lib/api/generated/models/RelationshipRightsControlsV1';
import { RelationshipEvidencePageV1FromJSON, type RelationshipEvidencePageV1 } from '@/lib/api/generated/models/RelationshipEvidencePageV1';

export interface RelationshipWorkspaceViews {
  workspace: RelationshipWorkspaceV1;
  plan: RelationshipPlanV1;
  attention: RelationshipAttentionPageV1;
  work: RelationshipWorkPageV1;
  results: RelationshipResultsV1;
  usageBudget: RelationshipUsageBudgetV1;
  rightsControls: RelationshipRightsControlsV1;
  evidence: RelationshipEvidencePageV1;
}

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

async function read(path: string, accessToken: string): Promise<unknown> {
  const response = await fetch(`${businessPlatformUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: 'no-store',
  });
  if (!response.ok) throw new Error(`Relationship Workspace request failed with ${response.status}.`);
  return response.json();
}

export async function getRelationshipWorkspaceViews(
  relationshipId: string,
  accessToken: string
): Promise<RelationshipWorkspaceViews> {
  const root = `/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/workspace`;
  const [workspace, plan, attention, work, results, usageBudget, rightsControls, evidence] = await Promise.all([
    read(root, accessToken), read(`${root}/plan`, accessToken), read(`${root}/attention`, accessToken),
    read(`${root}/work`, accessToken), read(`${root}/results`, accessToken),
    read(`${root}/usage-budget`, accessToken), read(`${root}/rights-controls`, accessToken),
    read(`${root}/evidence`, accessToken),
  ]);
  return {
    workspace: RelationshipWorkspaceV1FromJSON(workspace),
    plan: RelationshipPlanV1FromJSON(plan),
    attention: RelationshipAttentionPageV1FromJSON(attention),
    work: RelationshipWorkPageV1FromJSON(work),
    results: RelationshipResultsV1FromJSON(results),
    usageBudget: RelationshipUsageBudgetV1FromJSON(usageBudget),
    rightsControls: RelationshipRightsControlsV1FromJSON(rightsControls),
    evidence: RelationshipEvidencePageV1FromJSON(evidence),
  };
}