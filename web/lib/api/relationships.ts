import {
  EmploymentRelationshipFromJSON,
  type EmploymentRelationship,
} from '@/lib/api/generated/models/EmploymentRelationship';
import {
  RelationshipTimelineEntryFromJSON,
  type RelationshipTimelineEntry,
} from '@/lib/api/generated/models/RelationshipTimelineEntry';

export type { EmploymentRelationship, RelationshipTimelineEntry };

export interface RelationshipEvaluationProjection {
  relationshipId: string;
  lifecycleState: string;
  interviewState: string;
  context: Array<{ payloadReference: string; fieldType: string; value: unknown; status: string }>;
  nextContextQuestion?: string | null;
  trial?: { trialId: string; startsAt: string; expiresAt: string; status: string } | null;
  goals: Array<{ goalId: string; goal: string; measure: string; status: string; reviewCadenceMonths: number }>;
  skills: Array<{ configurationId: string; skillId: string; applicability: string; applicabilityReason?: string | null; authorityState: string; status: string }>;
  decisionSpace?: { version: number; budgetCeilingInrPaise: number; authorityBoundaries: unknown[]; stopConditions: unknown[]; reviewCadenceMonths: number } | null;
}

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

async function authorizedGet(path: string, accessToken: string): Promise<unknown> {
  const response = await fetch(`${businessPlatformUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: 'no-store',
  });
  if (!response.ok) throw new Error(`Business Platform request failed with ${response.status}.`);
  return response.json();
}

export async function getRelationship(relationshipId: string, accessToken: string) {
  const json = await authorizedGet(
    `/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}`,
    accessToken
  );
  return EmploymentRelationshipFromJSON(json);
}

export async function getRelationshipTimeline(relationshipId: string, accessToken: string) {
  const json = await authorizedGet(
    `/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/timeline`,
    accessToken
  );
  if (!Array.isArray(json)) throw new Error('Business Platform timeline response was not an array.');
  return json.map(RelationshipTimelineEntryFromJSON);
}

export async function getRelationshipEvaluation(
  relationshipId: string,
  accessToken: string,
): Promise<RelationshipEvaluationProjection> {
  return authorizedGet(
    `/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/evaluation`,
    accessToken,
  ) as Promise<RelationshipEvaluationProjection>;
}