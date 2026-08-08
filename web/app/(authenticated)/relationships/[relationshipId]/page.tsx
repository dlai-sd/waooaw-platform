import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { RelationshipWorkspace } from '@/components/relationships/RelationshipWorkspace';
import { getRelationship, getRelationshipTimeline } from '@/lib/api/relationships';
import { authOptions } from '@/lib/auth';

export default async function RelationshipPage({ params }: { params: { relationshipId: string } }) {
  const session = await getServerSession(authOptions);
  if (!session?.accessToken) redirect('/');

  const [relationship, timeline] = await Promise.all([
    getRelationship(params.relationshipId, session.accessToken),
    getRelationshipTimeline(params.relationshipId, session.accessToken),
  ]);
  return <RelationshipWorkspace relationship={relationship} timeline={timeline} />;
}