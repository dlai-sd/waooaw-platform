// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003; work-contracts/WC-167-acceptance-demo-readiness.md WC167-R001, WC167-R006
// Constitutional basis: C-009, C-023, C-059, C-063

import { redirect } from 'next/navigation';
import { AccessApprovals } from '@/components/admin/access/AccessApprovals';
import { RequestAccessPanel } from '@/components/admin/access/RequestAccessPanel';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken } from '@/lib/server-auth';
import { tokenSubject } from '@/lib/token-subject';

export const dynamic = 'force-dynamic';

// One page for every signed-in person: anyone can ask for a staff role; the Founder also decides on requests here.
export default async function RequestAccessPage() {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/home');
  const access = await resolvePlatformAccess(accessToken);
  return (
    <section aria-labelledby="access-title" className="portal-page providers-admin staff-access-page">
      <header className="portal-heading">
        <p className="eyebrow">Platform access</p>
        <h1 id="access-title">Staff access</h1>
        <p>
          Ask for a staff role, or, as the Founder, decide on requests. A role is granted only to a verified email and
          only after the Founder approves.
        </p>
      </header>
      <RequestAccessPanel access={access} subject={tokenSubject(accessToken)} />
      {access.founder ? <AccessApprovals /> : null}
    </section>
  );
}
