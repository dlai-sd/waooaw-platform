// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R024
// Constitutional basis: C-023, C-059, C-063, C-088

import { redirect } from 'next/navigation';
import { ProfessionalApprovals } from '@/components/admin/ProfessionalApprovals';
import { StateView } from '@/components/system/StateView';
import { asApprovals, type ProfessionalApproval } from '@/lib/professional-approvals';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken } from '@/lib/server-auth';
import { logServerFailure } from '@/lib/server-failure';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

async function loadApprovals(accessToken: string): Promise<ProfessionalApproval[] | null> {
  try {
    const response = await fetch(`${businessPlatformUrl}/api/v1/admin/professionals`, {
      headers: { Accept: 'application/json', Authorization: `Bearer ${accessToken}` },
      cache: 'no-store',
    });
    return response.ok ? asApprovals(await response.json()) : null;
  } catch (error) {
    logServerFailure('web.admin.professionals.list_failed', error);
    return null;
  }
}

export default async function ProfessionalsAdminPage() {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/home');
  if (!(await resolvePlatformAccess(accessToken)).founder) redirect('/403');
  const approvals = await loadApprovals(accessToken);
  if (approvals === null) {
    return (
      <StateView
        actionHref="/admin/professionals"
        actionLabel="Try again"
        description="The professionals could not be reached. Nothing was changed. Try again shortly."
        kind="error"
        title="Professionals are unavailable"
      />
    );
  }
  return (
    <section aria-labelledby="professionals-title" className="portal-page">
      <header className="portal-heading">
        <p className="eyebrow">Founder</p>
        <h1 id="professionals-title">Professionals</h1>
        <p>
          Decide which professionals customers may take on a Trial or Hire. Your approval covers every customer and is
          tied to the exact definition in this release. Approving, suspending or retiring needs a fresh strong sign-in,
          and every decision is recorded with your name and the time.
        </p>
      </header>
      <ProfessionalApprovals initial={approvals} />
    </section>
  );
}
