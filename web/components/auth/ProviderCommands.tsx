'use client';

// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md §5.1 Identity And Disclosure
// Constitutional basis: C-049 (Honest Limitation), C-063 (Data Minimisation)

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { FaApple, FaEnvelope, FaFacebookF, FaGoogle } from 'react-icons/fa6';
import { signIn } from 'next-auth/react';
import type { IdentityProvider } from '@/lib/api/generated/models/IdentityProvider';
import { recordAuthTransition } from '@/lib/auth-transition';

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

function supportsNextAuth(providerId: IdentityProvider['id']): providerId is keyof typeof nextAuthProvider {
  return providerId in nextAuthProvider;
}

function isActionable(provider: IdentityProvider) {
  return provider.availability === 'AVAILABLE' && (provider.id === 'GOOGLE' || provider.id === 'FACEBOOK');
}

export function ProviderCommands({ callbackUrl, intent, providers, reload = () => window.location.reload() }: {
  callbackUrl: string;
  intent: ProviderIntent;
  providers: IdentityProvider[];
  reload?: () => void;
}) {
  const [pendingProvider, setPendingProvider] = useState<string>();
  const [googleDisclosureOpen, setGoogleDisclosureOpen] = useState(false);
  const [launchFailure, setLaunchFailure] = useState<string>();
  const googleCommand = useRef<HTMLButtonElement>(null);
  const disclosure = useRef<HTMLDivElement>(null);
  const continueCommand = useRef<HTMLButtonElement>(null);
  const primary = providers.find((provider) => provider.id === 'GOOGLE');
  const secondary = providers.filter((provider) => provider.id !== 'GOOGLE');

  useEffect(() => {
    if (!googleDisclosureOpen) return;
    continueCommand.current?.focus();
    function handleDisclosureKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setGoogleDisclosureOpen(false);
        googleCommand.current?.focus();
        return;
      }
      if (event.key !== 'Tab') return;
      const commands = disclosure.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
      if (!commands?.length) return;
      const first = commands[0];
      const last = commands[commands.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        last.focus();
        event.preventDefault();
      } else if (!event.shiftKey && document.activeElement === last) {
        first.focus();
        event.preventDefault();
      }
    }
    window.addEventListener('keydown', handleDisclosureKey);
    return () => window.removeEventListener('keydown', handleDisclosureKey);
  }, [googleDisclosureOpen]);
  useEffect(() => {
    recordAuthTransition('PROVIDER_PROJECTION_READY');
  }, []);

  function actionLabel(provider: IdentityProvider) {
    const action = intent === 'login' ? 'Log in' : 'Sign up';
    return `${action} with ${provider.displayName}`;
  }

  async function begin(provider: IdentityProvider) {
    if (!isActionable(provider) || !supportsNextAuth(provider.id)) return;
    setLaunchFailure(undefined);
    setPendingProvider(provider.id);
    recordAuthTransition('BROKER_REDIRECT_REQUESTED');
    try {
      await signIn(nextAuthProvider[provider.id], { callbackUrl }, provider.id === 'GOOGLE' ? { prompt: 'select_account' } : undefined);
    } catch {
      setPendingProvider(undefined);
      setLaunchFailure('BROKER_LAUNCH_FAILED');
    }
  }

  function cancelGoogleDisclosure() {
    setGoogleDisclosureOpen(false);
    googleCommand.current?.focus();
  }

  const readinessUnavailable = providers.some((provider) => provider.unavailableReason === 'TEMPORARILY_UNAVAILABLE');

  return (
    <div className="provider-commands">
      {primary ? (() => {
        const Icon = icons[primary.id];
        const unavailable = !isActionable(primary);
        const label = actionLabel(primary);
        return (
          <button
            aria-label={unavailable ? `${label} (Unavailable)` : label}
            className="provider-command provider-command-primary"
            disabled={unavailable || pendingProvider !== undefined}
            onClick={() => setGoogleDisclosureOpen(true)}
            ref={googleCommand}
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
        const unavailable = !isActionable(provider);
        const label = actionLabel(provider);
        return (
          <button
            aria-label={unavailable ? `${label} (Unavailable)` : label}
            className={`provider-icon-command provider-command-${provider.id.toLowerCase()}`}
            disabled={unavailable || pendingProvider !== undefined}
            key={provider.id}
            onClick={() => void begin(provider)}
            title={unavailable ? `${provider.displayName} is unavailable` : label}
            type="button"
          >
            <Icon aria-hidden="true" size={20} />
            <span className="visually-hidden">{label}</span>
          </button>
        );
      })}
      </div>
      {readinessUnavailable ? <div className="provider-readiness" role="status">
        <p>Sign-in services are still starting.</p>
        <button className="text-command" type="button" onClick={reload}>Try again</button>
      </div> : null}
      {launchFailure ? <div className="provider-readiness" data-reason-code={launchFailure} role="alert"><p>Google sign-in could not start.</p><button className="text-command" onClick={() => setLaunchFailure(undefined)} type="button">Try again</button></div> : null}
      {googleDisclosureOpen && primary ? <div aria-labelledby="google-disclosure-title" aria-modal="true" className="provider-disclosure" ref={disclosure} role="dialog">
        <div className="provider-disclosure-content">
          <h2 id="google-disclosure-title">Continue to Google</h2>
          <p>WAOOAW will receive your name, email address, profile information and Google account identifier to sign you in, identify your WAOOAW account, and support registration only when you explicitly choose it. WAOOAW does not receive your Google password.</p>
          <p>Google manages its own consent screen. Read the WAOOAW <Link href="/privacy">Privacy Notice</Link> before continuing.</p>
          <div className="provider-disclosure-actions">
            <button className="text-command" onClick={cancelGoogleDisclosure} type="button">Cancel</button>
            <button className="primary-command" onClick={() => { setGoogleDisclosureOpen(false); void begin(primary); }} ref={continueCommand} type="button">Continue to Google</button>
          </div>
        </div>
      </div> : null}
    </div>
  );
}