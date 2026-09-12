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
  EMAIL: 'keycloak',
} as const;

const labels = {
  GOOGLE: 'Continue with Google',
  FACEBOOK: 'Continue with Facebook',
  APPLE: 'Continue with Apple',
  EMAIL: 'Continue with email',
} as const;

const icons = {
  GOOGLE: FaGoogle,
  FACEBOOK: FaFacebookF,
  APPLE: FaApple,
  EMAIL: FaEnvelope,
} as const;

function supportsNextAuth(providerId: IdentityProvider['id']): providerId is keyof typeof nextAuthProvider {
  return providerId in nextAuthProvider;
}

function isActionable(provider: IdentityProvider) {
  return provider.availability === 'AVAILABLE' && supportsNextAuth(provider.id);
}

export function ProviderCommands({ callbackUrl, providers }: { callbackUrl: string; providers: IdentityProvider[] }) {
  const [pendingProvider, setPendingProvider] = useState<string>();

  function begin(provider: IdentityProvider) {
    if (!isActionable(provider) || !supportsNextAuth(provider.id)) return;
    setPendingProvider(provider.id);
    void signIn(nextAuthProvider[provider.id], { callbackUrl });
  }

  const renderProvider = (provider: IdentityProvider) => {
        const Icon = icons[provider.id];
        const unavailable = !isActionable(provider);
        return (
          <button
            className={`provider-command provider-command-${provider.id.toLowerCase()}`}
            disabled={unavailable || pendingProvider !== undefined}
            key={provider.id}
            onClick={() => begin(provider)}
            type="button"
          >
            <Icon aria-hidden="true" size={20} />
            <span>{labels[provider.id]}</span>
            {unavailable ? <small>Coming soon</small> : null}
          </button>
        );
  };
  const available = providers.filter(isActionable);
  const unavailable = providers.filter((provider) => !isActionable(provider));

  return (
    <div className="provider-commands">
      {available.map(renderProvider)}
      {unavailable.length > 0 ? <p className="provider-coming-soon">Coming soon</p> : null}
      {unavailable.map(renderProvider)}
    </div>
  );
}