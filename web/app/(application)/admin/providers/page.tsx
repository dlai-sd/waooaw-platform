// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { ProvidersWorkspace } from '@/components/admin/providers/ProvidersWorkspace';
import { StateView } from '@/components/system/StateView';
import { loadProviders } from '@/lib/provider-admin-server';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken } from '@/lib/server-auth';
import { redirect } from 'next/navigation';

export default async function ProvidersPage() {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/home');
  if (!(await resolvePlatformAccess(accessToken)).founder) redirect('/home');
  const load = await loadProviders(accessToken);
  if (load.kind === 'forbidden') redirect('/home');
  if (load.kind === 'unavailable') {
    return (
      <StateView
        actionHref="/admin/providers"
        actionLabel="Try again"
        description="The provider registry could not be reached. Nothing was changed. Try again shortly."
        kind="error"
        title="Providers are unavailable"
      />
    );
  }
  return (
    <section aria-labelledby="providers-title" className="portal-page providers-admin">
      <header className="portal-heading">
        <p className="eyebrow">Provider credentials</p>
        <h1 id="providers-title">Providers</h1>
        <p>
          Enter, test and save the API keys WAOOAW uses. A saved value is used without a deployment and can never be
          read back. Only the Founder can change it.
        </p>
      </header>
      <ProvidersWorkspace initialProviders={load.providers} />
    </section>
  );
}
