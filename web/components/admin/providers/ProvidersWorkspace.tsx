'use client';

// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { useCallback, useState } from 'react';
import { providerCall } from '@/lib/provider-admin-call';
import { problemText, type ProviderSummary } from '@/lib/provider-admin-client';
import { AddProviderForm } from './AddProviderForm';
import { ProviderList } from './ProviderList';
import { ProviderPanel } from './ProviderPanel';

type Props = { initialProviders: ProviderSummary[] };

export function ProvidersWorkspace({ initialProviders }: Props) {
  const [providers, setProviders] = useState(initialProviders);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [userSelected, setUserSelected] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const result = await providerCall<ProviderSummary[]>('GET', '');
    if (result.ok && Array.isArray(result.data)) {
      setProviders(result.data);
      setRefreshError(null);
    } else {
      setRefreshError(
        `The provider list could not be refreshed. ${result.ok ? '' : problemText(result.problem)} Reload the page to see the latest status.`
      );
    }
  }, []);

  const selected = providers.find((provider) => provider.id === selectedId) ?? null;

  return (
    <div className="providers-layout">
      <div className="workbench-stack">
        <ProviderList
          onSelect={(id) => {
            setSelectedId(id);
            setUserSelected(true);
          }}
          providers={providers}
          selectedId={selectedId}
        />
        <AddProviderForm
          onCreated={(provider) => {
            setProviders((current) => [...current.filter((entry) => entry.id !== provider.id), provider]);
            setSelectedId(provider.id);
            setUserSelected(true);
          }}
        />
      </div>
      <div className="workbench-stack">
        {refreshError ? (
          <p className="workbench-message workbench-message-error" role="alert">
            {refreshError}
          </p>
        ) : null}
        {selected ? (
          <ProviderPanel
            focusOnMount={userSelected}
            key={selected.id}
            onChanged={() => void refresh()}
            provider={selected}
          />
        ) : (
          <section aria-label="Provider details" className="workbench-section providers-panel">
            <p className="workbench-hint">
              {providers.length === 0
                ? 'No providers are registered yet. Add one to get started.'
                : 'Select a provider to test and save its value, or to roll back to an earlier version.'}
            </p>
          </section>
        )}
      </div>
    </div>
  );
}
