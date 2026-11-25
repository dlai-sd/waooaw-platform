// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-059, ADR-051

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
import { getCustomerEngagementProgress } from '@/lib/api/customer-engagement';
import { getProfessionalDisclosure } from '@/lib/api/professionals';
import { getServerAccessToken } from '@/lib/server-auth';
import { getRequestI18n } from '@/lib/i18n-server';
import { getWorkbench } from '@/lib/api/workbench';
import { workbenchMessages } from '@/lib/workbench-i18n';
import { WorkbenchShell } from '@/components/workbench/WorkbenchShell';

export default async function RelationshipPage({
  params,
  searchParams,
}: {
  params: Promise<{ relationshipId: string }>;
  searchParams?: Promise<{ handoff?: string | string[]; surface?: string | string[] }>;
}) {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/login');
  const { relationshipId } = await params;
  const query = await searchParams;
  const handoff = query?.handoff;
  const surface = query?.surface;

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
  const workbench = await getWorkbench(relationshipId, accessToken);
  if (workbench.state === 'available') {
    const { locale } = await getRequestI18n();
    return (
      <WorkbenchShell
        copy={workbenchMessages(locale)}
        handoffToken={typeof handoff === 'string' ? handoff : undefined}
        initial={workbench.snapshot}
        initialSurface={typeof surface === 'string' ? surface : undefined}
        relationshipId={relationshipId}
      />
    );
  }
  const [workspaceViews, employment, engagementProgress] = await Promise.all([
    getRelationshipWorkspaceViews(relationshipId, accessToken),
    getEmploymentWorkspace(relationshipId, accessToken),
    getCustomerEngagementProgress(relationshipId, accessToken),
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
      engagementProgress={engagementProgress}
    />
  );
}
