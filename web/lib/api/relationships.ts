import 'server-only';

import { EmploymentApi } from '@/lib/api/generated/apis/EmploymentApi';
import { RelationshipWorkspaceApi } from '@/lib/api/generated/apis/RelationshipWorkspaceApi';
import type { EmploymentRelationshipCollectionV1 } from '@/lib/api/generated/models/EmploymentRelationshipCollectionV1';
import {
  EmploymentRelationshipFromJSON,
  type EmploymentRelationship,
} from '@/lib/api/generated/models/EmploymentRelationship';
import {
  RelationshipTimelineEntryFromJSON,
  type RelationshipTimelineEntry,
} from '@/lib/api/generated/models/RelationshipTimelineEntry';
import { Configuration } from '@/lib/api/generated/runtime';

export type { EmploymentRelationship, RelationshipTimelineEntry };

export interface RelationshipEvaluationProjection {
  relationshipId: string;
  lifecycleState: string;
  interviewState: string;
  context: Array<{ payloadReference: string; fieldType: string; value: unknown; status: string }>;
  nextContextQuestion?: string | null;
  trial?: { trialId: string; startsAt: string; expiresAt: string; status: string } | null;
  goals: Array<{ goalId: string; goal: string; measure: string; status: string; reviewCadenceMonths: number }>;
  skills: Array<{ configurationId: string; skillId: string; skillVersion: string; subjectVersion: string; applicability: string; applicabilityReason?: string | null; authorityState: string; status: string }>;
  decisionSpace?: { version: number; budgetCeilingInrPaise: number; authorityBoundaries: unknown[]; stopConditions: unknown[]; reviewCadenceMonths: number } | null;
}

export interface ContractJourneyProjection {
  contractId: string;
  version: number;
  contractHash: string;
  relationshipState: string;
  acceptanceState: string;
  paymentState: string;
  activationState: string;
  document: {
    professionalDisplayName: string;
    rights: string[];
    obligations: string[];
    limitations: string[];
    authorityTerms: string[];
    stopTerms: string[];
    priceTax: { currency: string; grossAmountInrPaise: number; gstAmountInrPaise: number; cadence: string; subscriptionTerms: string; adSpendTreatment: string; cancellationAndRefundTerms: string };
  };
}

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

export async function listEmploymentRelationships(
  accessToken: string,
  cursor?: string,
): Promise<EmploymentRelationshipCollectionV1> {
  const api = new EmploymentApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
  return api.listEmploymentRelationships(
    { cursor, limit: 24 },
    { cache: 'no-store' },
  );
}

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
  const api = new RelationshipWorkspaceApi(new Configuration({ basePath: businessPlatformUrl, accessToken }));
  return api.getRelationshipEvaluation(
    { relationshipId },
    { cache: 'no-store' },
  ) as unknown as Promise<RelationshipEvaluationProjection>;
}

export async function getContractJourney(
  relationshipId: string, accessToken: string,
): Promise<ContractJourneyProjection | null> {
  const response = await fetch(`${businessPlatformUrl}/api/v1/employment/relationships/${encodeURIComponent(relationshipId)}/contract-journey`, {
    headers: { Authorization: `Bearer ${accessToken}` }, cache: 'no-store',
  });
  if (response.status === 204) return null;
  if (!response.ok) throw new Error(`Business Platform request failed with ${response.status}.`);
  return response.json() as Promise<ContractJourneyProjection>;
}