'use client';

import { InteractionRequiredAuthError, PublicClientApplication } from '@azure/msal-browser';
import { KeyRound, Save } from 'lucide-react';
import { useRef, useState } from 'react';
import type { FormEvent } from 'react';

interface AzureKeyVaultWriterProps {
  adminEmail: string;
  clientId: string;
  environment: string;
  tenantId: string;
  vaultHost: string;
}

const vaultScopes = ['https://vault.azure.net/user_impersonation'];

export function AzureKeyVaultWriter({
  adminEmail,
  clientId,
  environment,
  tenantId,
  vaultHost,
}: AzureKeyVaultWriterProps) {
  const client = useRef<PublicClientApplication>();
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [message, setMessage] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus('saving');
    setMessage('');
    const form = event.currentTarget;
    const formData = new FormData(form);
    const name = String(formData.get('name') ?? '').trim();
    const value = String(formData.get('value') ?? '');
    try {
      client.current ??= new PublicClientApplication({
        auth: {
          clientId,
          authority: `https://login.microsoftonline.com/${tenantId}`,
          redirectUri: `${window.location.origin}/admin/azure-key-vault`,
        },
        cache: { cacheLocation: 'memoryStorage' },
      });
      await client.current.initialize();
      let account = client.current
        .getAllAccounts()
        .find((candidate) => candidate.username.toLowerCase() === adminEmail);
      if (!account) {
        const login = await client.current.loginPopup({ scopes: vaultScopes, loginHint: adminEmail });
        account = login.account;
      }
      let azureAccessToken: string;
      try {
        azureAccessToken = (await client.current.acquireTokenSilent({ account, scopes: vaultScopes })).accessToken;
      } catch (error) {
        if (!(error instanceof InteractionRequiredAuthError)) throw error;
        azureAccessToken = (await client.current.acquireTokenPopup({ account, scopes: vaultScopes })).accessToken;
      }
      const response = await fetch('/api/admin/azure-key-vault', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${azureAccessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, value }),
      });
      const outcome = (await response.json().catch(() => ({}))) as { title?: string };
      if (!response.ok) throw new Error(outcome.title ?? 'Azure Key Vault could not save the secret.');
      form.reset();
      setStatus('saved');
      setMessage(`Saved ${name} to ${environment}. The value cannot be read from this page.`);
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Azure Key Vault could not save the secret.');
    }
  }

  return (
    <section className="key-vault-writer" aria-labelledby="key-vault-writer-title">
      <header>
        <KeyRound aria-hidden="true" size={24} />
        <div>
          <p className="section-label">{environment} environment</p>
          <h2 id="key-vault-writer-title">Add or overwrite a secret</h2>
          <p>{vaultHost}</p>
        </div>
      </header>
      <form className="portal-form" onSubmit={submit}>
        <label>
          Secret name
          <input autoComplete="off" maxLength={127} name="name" pattern="[0-9A-Za-z\\-]+" required />
        </label>
        <label>
          Secret value
          <input autoComplete="new-password" maxLength={16384} name="value" required type="password" />
        </label>
        <button className="primary-command" disabled={status === 'saving'} type="submit">
          <Save aria-hidden="true" size={18} />
          {status === 'saving' ? 'Authorizing and saving...' : 'Save to Azure Key Vault'}
        </button>
        <output aria-live="polite" className={`form-status ${status === 'error' ? 'error-copy' : ''}`}>
          {message}
        </output>
      </form>
    </section>
  );
}
