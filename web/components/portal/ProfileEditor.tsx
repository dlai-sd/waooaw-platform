'use client';

import { useState } from 'react';

export function ProfileEditor({ displayName, organizationDisplayName }: { displayName: string; organizationDisplayName: string }) {
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  async function submit(formData: FormData) {
    setStatus('saving');
    const response = await fetch('/api/identity/profile', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ displayName: formData.get('displayName'), organizationDisplayName: formData.get('organizationDisplayName'), idempotencyKey: crypto.randomUUID() }),
    });
    setStatus(response.ok ? 'saved' : 'error');
  }

  return <form className="portal-form" action={(formData) => void submit(formData)}><label>Display name<input name="displayName" defaultValue={displayName} required maxLength={120} /></label><label>Organization<input name="organizationDisplayName" defaultValue={organizationDisplayName} required maxLength={160} /></label><button className="primary-command" disabled={status === 'saving'} type="submit">{status === 'saving' ? 'Saving…' : 'Save profile'}</button><span role="status">{status === 'saved' ? 'Profile saved.' : status === 'error' ? 'Profile could not be saved.' : ''}</span></form>;
}