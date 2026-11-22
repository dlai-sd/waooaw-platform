// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import {
  categoryHeadings,
  credentialLabel,
  outcomeLabel,
  type ProviderCategory,
  type ProviderSummary,
} from '@/lib/provider-admin-client';

const categories: ProviderCategory[] = ['PLATFORM_LLM', 'AGENT_API'];

export function ProviderStatusChips({ provider }: { provider: ProviderSummary }) {
  const { credential } = provider;
  return (
    <span className="providers-chips">
      <span className="status-label providers-chip" data-tone={credential.status === 'ACTIVE' ? 'ok' : 'muted'}>
        {credentialLabel(provider)}
      </span>
      {credential.lastTestOutcome ? (
        <span
          className="status-label providers-chip"
          data-tone={
            credential.lastTestOutcome === 'PASSED' ? 'ok' : credential.lastTestOutcome === 'FAILED' ? 'bad' : 'muted'
          }
        >
          {outcomeLabel[credential.lastTestOutcome]}
        </span>
      ) : null}
      {provider.active ? null : (
        <span className="status-label providers-chip" data-tone="muted">
          Inactive
        </span>
      )}
    </span>
  );
}

type Props = {
  providers: ProviderSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
};

export function ProviderList({ providers, selectedId, onSelect }: Props) {
  return (
    <div className="providers-groups">
      {categories.map((category) => {
        const group = providers.filter((provider) => provider.category === category);
        const headingId = `providers-group-${category}`;
        return (
          <section aria-labelledby={headingId} className="workbench-section" key={category}>
            <h2 id={headingId}>{categoryHeadings[category]}</h2>
            {group.length === 0 ? (
              <p className="workbench-hint">No providers here yet. Use Add provider below.</p>
            ) : (
              <ul className="providers-list">
                {group.map((provider) => (
                  <li key={provider.id}>
                    <button
                      aria-current={provider.id === selectedId ? 'true' : undefined}
                      className="providers-item"
                      onClick={() => onSelect(provider.id)}
                      type="button"
                    >
                      <span className="providers-item-name">
                        <strong>{provider.displayName}</strong>
                        <span className="workbench-hint">
                          {provider.providerName}
                          {provider.agentTypeId ? ` · ${provider.agentTypeId}` : ''}
                        </span>
                      </span>
                      <ProviderStatusChips provider={provider} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
