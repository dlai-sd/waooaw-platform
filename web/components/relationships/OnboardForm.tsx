'use client';

import { useState } from 'react';

export function OnboardForm({ relationshipId, summary }: { relationshipId: string; summary?: string }) {
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  async function submit(formData: FormData) {
    setStatus('saving');
    const response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/onboard`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idempotencyKey: crypto.randomUUID(), onboard: { schemaVersion: '1.0.0', preferredAgentDisplayName: formData.get('preferredAgentDisplayName') || undefined, chatAppearance: formData.get('chatAppearance'), timestampVisibility: formData.get('timestampVisibility'), themePreference: formData.get('themePreference') } }),
    });
    setStatus(response.ok ? 'saved' : 'error');
  }
  return <form className="portal-form onboard-form" onSubmit={(event) => { event.preventDefault(); void submit(new FormData(event.currentTarget)); }}><p>{summary ?? 'Choose lightweight presentation preferences. Induction continues in conversation.'}</p><label>Agent display name<input name="preferredAgentDisplayName" maxLength={80} placeholder="Optional" /></label><label>Chat appearance<select name="chatAppearance" defaultValue="CONSTITUTIONAL"><option value="CONSTITUTIONAL">Constitutional</option><option value="COMPACT">Compact</option></select></label><label>Timestamps<select name="timestampVisibility" defaultValue="RELATIVE"><option value="RELATIVE">Relative</option><option value="ABSOLUTE">Absolute</option></select></label><label>Theme<select name="themePreference" defaultValue="SYSTEM"><option value="SYSTEM">System</option><option value="LIGHT">Light</option><option value="DARK">Dark</option></select></label><button className="primary-command" disabled={status === 'saving'} type="submit">{status === 'saving' ? 'Saving…' : 'Save Onboard preferences'}</button><span role="status">{status === 'saved' ? 'Onboard preferences saved.' : status === 'error' ? 'Onboard preferences could not be saved.' : ''}</span></form>;
}