'use client';

// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Constitutional basis: C-049 (Honest Limitation), C-063 (Data Minimisation)

import { useState } from 'react';
import { FaApple, FaEnvelope, FaFacebookF, FaGoogle } from 'react-icons/fa6';
import { signIn } from 'next-auth/react';
import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';

const nextAuthProvider = {
  GOOGLE: 'keycloak-google',
  FACEBOOK: 'keycloak-facebook',
  APPLE: 'keycloak-apple',
  EMAIL: 'keycloak',
} as const;

const icons = {
  GOOGLE: FaGoogle,
  FACEBOOK: FaFacebookF,
  APPLE: FaApple,
  EMAIL: FaEnvelope,
} as const;

type ProviderIntent = 'login' | 'register';

export function ProviderCommands({ callbackUrl, intent, providers }: {
  callbackUrl: string;
  intent: ProviderIntent;
  providers: IdentityProvider[];
}) {
  const [pendingProvider, setPendingProvider] = useState<string>();
  const primary = providers.find((provider) => provider.id === 'GOOGLE');
  const secondary = providers.filter((provider) => provider.id !== 'GOOGLE');

  function actionLabel(provider: IdentityProvider) {
    const action = intent === 'login' ? 'Log in' : 'Sign up';
    return `${action} with ${provider.displayName}`;
  }

  function begin(provider: IdentityProvider) {
    if (provider.availability !== 'AVAILABLE') return;
    setPendingProvider(provider.id);
    void signIn(nextAuthProvider[provider.id], { callbackUrl });
  }

  return (
    <div className="provider-commands">
      {primary ? (() => {
        const Icon = icons[primary.id];
        const unavailable = primary.availability !== 'AVAILABLE';
        const label = actionLabel(primary);
        return (
          <button
            aria-label={unavailable ? `${label} (Unavailable)` : label}
            className="provider-command provider-command-primary"
            disabled={unavailable || pendingProvider !== undefined}
            onClick={() => begin(primary)}
            title={unavailable ? `${primary.displayName} is unavailable` : label}
            type="button"
          >
            <Icon aria-hidden="true" size={20} />
            <span>{label}</span>
          </button>
        );
      })() : null}
      <div className="provider-secondary">
      {secondary.map((provider) => {
        const Icon = icons[provider.id];
        const unavailable = provider.availability !== 'AVAILABLE';
        const label = actionLabel(provider);
        return (
          <button
            aria-label={unavailable ? `${label} (Unavailable)` : label}
            className={`provider-icon-command provider-command-${provider.id.toLowerCase()}`}
            disabled={unavailable || pendingProvider !== undefined}
            key={provider.id}
            onClick={() => begin(provider)}
            title={unavailable ? `${provider.displayName} is unavailable` : label}
            type="button"
          >
            <Icon aria-hidden="true" size={20} />
            <span className="visually-hidden">{label}</span>
          </button>
        );
      })}
      </div>
    </div>
  );
}