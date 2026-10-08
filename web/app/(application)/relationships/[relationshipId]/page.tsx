import { redirect } from 'next/navigation';
import { RelationshipWorkspace } from '@/components/relationships/RelationshipWorkspace';
import { RelationshipPreActivation } from '@/components/relationships/RelationshipPreActivation';
import {
  getContractJourney,
  getRelationship,
  getRelationshipEvaluation,
  getRelationshipTimeline,
  listEmploymentRelationships,
} from '@/lib/api/relationships';
import { getRelationshipWorkspaceViews } from '@/lib/api/relationship-workspace';
import { getEmploymentWorkspace } from '@/lib/api/employment-workspace';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function RelationshipPage({ params }: { params: Promise<{ relationshipId: string }> }) {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/login');
  const { relationshipId } = await params;

  const relationship = await getRelationship(relationshipId, accessToken);
  const operational = relationship.state === 'TRIAL_ACTIVE' || relationship.state === 'ACTIVE';
  const [timeline, evaluation, contractJourney, relationships] = await Promise.all([
    getRelationshipTimeline(relationshipId, accessToken),
    getRelationshipEvaluation(relationshipId, accessToken),
    getContractJourney(relationshipId, accessToken),
    listEmploymentRelationships(accessToken),
  ]);
  if (!operational) {
    const disclosure =
      relationship.state === 'CONFIGURING' ? await getProfessionalDisclosure(relationship.professionalType) : null;
    return (
      <RelationshipPreActivation
        relationship={relationship}
        relationships={relationships.items}
        timeline={timeline}
        evaluation={evaluation}
        contractJourney={contractJourney}
        availableSkills={disclosure?.skills ?? []}
      />
    );
  }
  const [workspaceViews, employment] = await Promise.all([
    getRelationshipWorkspaceViews(relationshipId, accessToken),
    getEmploymentWorkspace(relationshipId, accessToken),
  ]);
  return (
    <RelationshipWorkspace
      relationship={relationship}
      relationships={relationships.items}
      timeline={timeline}
      views={workspaceViews}
      evaluation={evaluation}
      contractJourney={contractJourney}
      employment={employment}
    />
  );
}
