import { redirect } from 'next/navigation';
import { RelationshipWorkspace } from '@/components/relationships/RelationshipWorkspace';
import { getRelationship, getRelationshipTimeline } from '@/lib/api/relationships';
import { getRelationshipWorkspaceViews } from '@/lib/api/relationship-workspace';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function RelationshipPage({ params }: { params: { relationshipId: string } }) {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/login');

  const [relationship, timeline, workspaceViews] = await Promise.all([
    getRelationship(params.relationshipId, accessToken),
    getRelationshipTimeline(params.relationshipId, accessToken),
    getRelationshipWorkspaceViews(params.relationshipId, accessToken),
  ]);
  return <RelationshipWorkspace relationship={relationship} timeline={timeline} views={workspaceViews} />;
}