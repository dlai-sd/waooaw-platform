'use client';

// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R004
// Constitutional basis: C-042 (Localization), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { useState } from 'react';
import type { NotificationPreferences } from '@/lib/api/generated/models/NotificationPreferences';
import { NotificationChannel } from '@/lib/api/generated/models/NotificationChannel';
import { resolveLocale, supportedLocales, type SupportedLocale } from '@/lib/preferences';

const languageNames: Record<SupportedLocale, string> = {
  en: 'English',
  hi: 'हिन्दी (Hindi)',
  mr: 'मराठी (Marathi)',
  ta: 'தமிழ் (Tamil)',
  te: 'తెలుగు (Telugu)',
  kn: 'ಕನ್ನಡ (Kannada)',
  gu: 'ગુજરાતી (Gujarati)',
  bn: 'বাংলা (Bengali)',
  ml: 'മലയാളം (Malayalam)',
  pa: 'ਪੰਜਾਬੀ (Punjabi)',
  ur: 'اردو (Urdu)',
};

const channelLabels: Array<[NotificationChannel, string]> = [
  [NotificationChannel.InApp, 'In the app'],
  [NotificationChannel.Email, 'Email'],
  [NotificationChannel.Whatsapp, 'WhatsApp'],
];

const kinds: Array<[keyof NotificationPreferences, string]> = [
  ['approvalRequests', 'Approval requests'],
  ['maturityReports', 'Maturity reports'],
  ['monthlyNarratives', 'Monthly narratives'],
  ['selfGovernanceAlerts', 'Self-governance alerts'],
];

export function SettingsEditor({
  locale,
  notificationPreferences,
  theme,
  timestampVisibility,
}: { locale: string; notificationPreferences: NotificationPreferences; theme: string; timestampVisibility: string }) {
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error' | 'approvals'>('idle');
  const selectedTheme = theme === 'LIGHT' ? 'LIGHT' : 'DARK';
  async function submit(formData: FormData) {
    const chosen = Object.fromEntries(
      kinds.map(([kind]) => [kind, formData.getAll(kind).map(String) as NotificationChannel[]])
    ) as unknown as NotificationPreferences;
    // An approval request that reaches nowhere would silently block work, so at least one channel stays on.
    if (chosen.approvalRequests.length === 0) {
      setStatus('approvals');
      return;
    }
    setStatus('saving');
    const response = await fetch('/api/identity/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        idempotencyKey: crypto.randomUUID(),
        settings: {
          schemaVersion: '1.0.0',
          locale: formData.get('locale'),
          theme: formData.get('theme'),
          timestampVisibility: formData.get('timestampVisibility'),
          notificationPreferences: chosen,
        },
      }),
    });
    setStatus(response.ok ? 'saved' : 'error');
    if (response.ok) {
      document.cookie = `waooaw-locale=${formData.get('locale')}; Path=/; Max-Age=31536000; SameSite=Lax`;
      document.cookie = `waooaw-theme=${String(formData.get('theme')).toLowerCase()}; Path=/; Max-Age=31536000; SameSite=Lax`;
    }
  }
  return (
    <form
      className="portal-form portal-form-inline"
      onSubmit={(event) => {
        event.preventDefault();
        void submit(new FormData(event.currentTarget));
      }}
    >
      <label>
        Language
        <select name="locale" defaultValue={resolveLocale(locale)}>
          {supportedLocales.map((code) => (
            <option key={code} value={code}>
              {languageNames[code]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Theme
        <select name="theme" defaultValue={selectedTheme}>
          <option value="LIGHT">Light</option>
          <option value="DARK">Dark</option>
        </select>
      </label>
      <label>
        Timestamps
        <select name="timestampVisibility" defaultValue={timestampVisibility}>
          <option value="RELATIVE">Relative</option>
          <option value="ABSOLUTE">Absolute</option>
        </select>
      </label>
      {kinds.map(([kind, label]) => (
        <fieldset key={kind}>
          <legend>{label}</legend>
          {channelLabels.map(([channel, channelLabel]) => (
            <label key={channel}>
              <input
                type="checkbox"
                name={kind}
                value={channel}
                defaultChecked={notificationPreferences[kind].includes(channel)}
              />
              {channelLabel}
            </label>
          ))}
        </fieldset>
      ))}
      <button className="primary-command" disabled={status === 'saving'} type="submit">
        {status === 'saving' ? 'Saving…' : 'Save settings'}
      </button>
      <output>
        {status === 'saved'
          ? 'Settings saved.'
          : status === 'error'
            ? 'Settings could not be saved. Nothing was changed. Please try again.'
            : status === 'approvals'
              ? 'Keep at least one way to receive approval requests, so nothing waits for you unseen.'
              : ''}
      </output>
    </form>
  );
}
