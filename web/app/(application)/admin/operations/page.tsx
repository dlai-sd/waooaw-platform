// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008, WC171-R009, WC171-R010
// Constitutional basis: C-023, C-049, C-059, C-063

import { OperationsConsole } from '@/components/admin/operations/OperationsConsole';
import { DataRequestsPanel } from '@/components/admin/operations/DataRequestsPanel';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken } from '@/lib/server-auth';
import { redirect } from 'next/navigation';

export default async function OperationsPage() {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/home');
  const access = await resolvePlatformAccess(accessToken);
  // The Business Platform decides who may read or resolve; a person with no staff grant never sees this screen.
  if (!access.founder && !access.administrator) redirect('/403');
  return (
    <section aria-labelledby="operations-title" className="portal-page operations-console">
      <header className="portal-heading">
        <p className="eyebrow">Operations</p>
        <h1 id="operations-title">What needs attention</h1>
        <p>
          Blocked messages, alert delivery, customers and service health, without database access. Only the Founder can
          unblock or close a blocked message; nothing is ever deleted.
        </p>
      </header>
      <OperationsConsole canResolve={access.founder} />
      {access.founder ? <DataRequestsPanel canResolve /> : null}
    </section>
  );
}
