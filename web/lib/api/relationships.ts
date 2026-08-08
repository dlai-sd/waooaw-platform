import {
  EmploymentRelationshipFromJSON,
  type EmploymentRelationship,
} from '@/lib/api/generated/models/EmploymentRelationship';
import {
  RelationshipTimelineEntryFromJSON,
  type RelationshipTimelineEntry,
} from '@/lib/api/generated/models/RelationshipTimelineEntry';

export type { EmploymentRelationship, RelationshipTimelineEntry };

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