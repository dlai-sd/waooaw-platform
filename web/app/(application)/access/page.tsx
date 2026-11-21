// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003
// Constitutional basis: C-009, C-023, C-059, C-063

import { redirect } from 'next/navigation';
import { RequestAccessPanel } from '@/components/admin/access/RequestAccessPanel';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken } from '@/lib/server-auth';

export const dynamic = 'force-dynamic';

export default async function RequestAccessPage() {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/home');
  const access = await resolvePlatformAccess(accessToken);
  return (
    <main>
      <RequestAccessPanel access={access} />
    </main>
  );
}
