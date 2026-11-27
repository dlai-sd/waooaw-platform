// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R028, R032
// Constitutional basis: C-023, C-059, C-063, C-088

import { redirect } from 'next/navigation';
import { AgentOperationSettings, type OperationSettings } from '@/components/founder/AgentOperationSettings';
import { StateView } from '@/components/system/StateView';
import { operationMessages } from '@/lib/operation-i18n';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken } from '@/lib/server-auth';
import { logServerFailure } from '@/lib/server-failure';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

async function loadSettings(accessToken: string): Promise<OperationSettings | null> {
  try {
    const response = await fetch(`${businessPlatformUrl}/api/v1/admin/agent-operation/settings`, {
      headers: { Accept: 'application/json', Authorization: `Bearer ${accessToken}` },
      cache: 'no-store',
    });
    return response.ok ? ((await response.json()) as OperationSettings) : null;
  } catch (error) {
    logServerFailure('web.admin.agent_operation.settings_failed', error);
    return null;
  }
}

export default async function AgentOperationAdminPage() {
  const accessToken = await getServerAccessToken();
  if (!accessToken) redirect('/home');
  if (!(await resolvePlatformAccess(accessToken)).founder) redirect('/403');
  const settings = await loadSettings(accessToken);
  if (settings === null) {
    return (
      <StateView
        actionHref="/admin/agent-operation"
        actionLabel="Try again"
        description="The agent operation settings could not be reached. Nothing was changed. Try again shortly."
        kind="error"
        title="Agent operation is unavailable"
      />
    );
  }
  const copy = operationMessages('en');
  return (
    <section aria-labelledby="agent-operation-title" className="portal-page">
      <header className="portal-heading">
        <p className="eyebrow">Founder</p>
        <h1 id="agent-operation-title">{copy.settingsTitle}</h1>
        <p>
          Set how many conversations each package includes (the default is 1,000), which connectors customers may use,
          and where posts may be published. Only the Founder can change these, and saving needs a fresh strong sign-in.
        </p>
      </header>
      <AgentOperationSettings copy={copy} initial={settings} />
    </section>
  );
}
