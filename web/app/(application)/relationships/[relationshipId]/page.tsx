import { redirect } from 'next/navigation';
import { RelationshipWorkspace } from '@/components/relationships/RelationshipWorkspace';
import { getContractJourney, getRelationship, getRelationshipEvaluation, getRelationshipTimeline, listEmploymentRelationships } from '@/lib/api/relationships';
import { getRelationshipWorkspaceViews } from '@/lib/api/relationship-workspace';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function RelationshipPage({ params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/login');
  const { relationshipId } = await params;

  const [relationship, timeline, workspaceViews, evaluation, contractJourney, relationships] = await Promise.all([
    getRelationship(relationshipId, accessToken),
    getRelationshipTimeline(relationshipId, accessToken),
    getRelationshipWorkspaceViews(relationshipId, accessToken),
    getRelationshipEvaluation(relationshipId, accessToken),
    getContractJourney(relationshipId, accessToken),
    listEmploymentRelationships(accessToken),
  ]);
  return <RelationshipWorkspace relationship={relationship} relationships={relationships.items} timeline={timeline} views={workspaceViews} evaluation={evaluation} contractJourney={contractJourney} />;
}