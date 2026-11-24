// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R010
// Constitutional basis: C-026, C-059, C-063

import { ConnectionsWorkspace } from '@/components/connections/ConnectionsWorkspace';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { noticeFromParams } from '@/lib/provider-connections-client';
import { getServerAccessToken } from '@/lib/server-auth';

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

// The return address carries only fixed codes; anything else is ignored so no query text is ever rendered.
export default async function ConnectionsPage({ searchParams }: { searchParams: SearchParams }) {
  const accessToken = await getServerAccessToken();
  const staff = accessToken ? (await resolvePlatformAccess(accessToken)).administrator : false;
  return (
    <section aria-labelledby="connections-title" className="portal-page providers-admin connections-page">
      <header className="portal-heading">
        <p className="eyebrow">Connected accounts</p>
        <h1 id="connections-title">Connections</h1>
        <p>
          Connect your Facebook Page so your agent can publish posts you approve. You stay in control: connect,
          reconnect or revoke at any time.
        </p>
      </header>
      <ConnectionsWorkspace initialNotice={noticeFromParams(await searchParams)} staff={staff} />
    </section>
  );
}
