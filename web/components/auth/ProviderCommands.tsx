'use client';

// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Constitutional basis: C-049 (Honest Limitation), C-063 (Data Minimisation)

import { useState } from 'react';
import { FaApple, FaEnvelope, FaFacebookF, FaGoogle, FaWhatsapp } from 'react-icons/fa6';
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

export function ProviderCommands({ callbackUrl, providers }: { callbackUrl: string; providers: IdentityProvider[] }) {
  const [pendingProvider, setPendingProvider] = useState<string>();
  const [appleMessage, setAppleMessage] = useState(false);

  function begin(provider: IdentityProvider) {
    if (provider.id === 'APPLE') {
      setAppleMessage(true);
      return;
    }
    if (provider.availability !== 'AVAILABLE') return;
    setPendingProvider(provider.id);
    void signIn(nextAuthProvider[provider.id], { callbackUrl });
  }

  return (
    <div className="provider-commands">
      {providers.map((provider) => {
        const Icon = icons[provider.id];
        const unavailable = provider.id !== 'APPLE' && provider.availability !== 'AVAILABLE';
        return (
          <button
            aria-describedby={provider.id === 'APPLE' && appleMessage ? 'apple-integration-status' : undefined}
            className={`provider-command provider-command-${provider.id.toLowerCase()}`}
            disabled={unavailable || pendingProvider !== undefined}
            key={provider.id}
            onClick={() => begin(provider)}
            type="button"
          >
            <Icon aria-hidden="true" size={20} />
            <span>{labels[provider.id]}</span>
            {unavailable ? <small>Unavailable</small> : null}
          </button>
        );
      })}
      {appleMessage ? (
        <p className="provider-status" id="apple-integration-status" role="alert">
          <strong>Apple is coming soon.</strong> Meanwhile, use an available Google, Facebook, or email option. WhatsApp registration remains available only through its approved identity flow.
          <FaWhatsapp aria-hidden="true" size={18} />
        </p>
      ) : null}
    </div>
  );
}