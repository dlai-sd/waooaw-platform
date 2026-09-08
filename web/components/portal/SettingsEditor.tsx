'use client';

import { useState } from 'react';
import type { NotificationPreferences } from '@/lib/api/generated/models/NotificationPreferences';

export function SettingsEditor({ locale, notificationPreferences, theme, timestampVisibility }: { locale: string; notificationPreferences: NotificationPreferences; theme: string; timestampVisibility: string }) {
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  async function submit(formData: FormData) {
    setStatus('saving');
    const response = await fetch('/api/identity/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idempotencyKey: crypto.randomUUID(), settings: { schemaVersion: '1.0.0', locale: formData.get('locale'), theme: formData.get('theme'), timestampVisibility: formData.get('timestampVisibility'), notificationPreferences } }) });
    setStatus(response.ok ? 'saved' : 'error');
    if (response.ok) {
      document.cookie = `waooaw-locale=${formData.get('locale')}; Path=/; Max-Age=31536000; SameSite=Lax`;
      document.cookie = `waooaw-theme=${String(formData.get('theme')).toLowerCase()}; Path=/; Max-Age=31536000; SameSite=Lax`;
    }
  }
  return <form className="portal-form portal-form-inline" onSubmit={(event) => { event.preventDefault(); void submit(new FormData(event.currentTarget)); }}><label>Locale<input name="locale" defaultValue={locale} required /></label><label>Theme<select name="theme" defaultValue={theme}><option value="SYSTEM">System</option><option value="LIGHT">Light</option><option value="DARK">Dark</option></select></label><label>Timestamps<select name="timestampVisibility" defaultValue={timestampVisibility}><option value="RELATIVE">Relative</option><option value="ABSOLUTE">Absolute</option></select></label><button className="primary-command" disabled={status === 'saving'} type="submit">{status === 'saving' ? 'Saving…' : 'Save settings'}</button><span role="status">{status === 'saved' ? 'Settings saved.' : status === 'error' ? 'Settings could not be saved.' : ''}</span></form>;
}